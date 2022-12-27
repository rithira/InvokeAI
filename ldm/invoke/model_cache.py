'''
Manage a cache of Stable Diffusion model files for fast switching.
They are moved between GPU and CPU as necessary. If CPU memory falls
below a preset minimum, the least recently used model will be
cleared and loaded from disk when next needed.
'''
from __future__ import annotations

import contextlib
import gc
import hashlib
import io
import os
import sys
import textwrap
import time
import traceback
import warnings
from pathlib import Path
from typing import Union, Any

import torch
import transformers
from diffusers import AutoencoderKL, logging as dlogging
from omegaconf import OmegaConf
from omegaconf.dictconfig import DictConfig
from omegaconf.errors import ConfigAttributeError
from picklescan.scanner import scan_file_path

from ldm.invoke.generator.diffusers_pipeline import StableDiffusionGeneratorPipeline
from ldm.invoke.globals import Globals, global_models_dir, global_autoscan_dir
from ldm.util import instantiate_from_config, ask_user

DEFAULT_MAX_MODELS=2

class ModelCache(object):
    def __init__(self, config:OmegaConf, device_type:str, precision:str, max_loaded_models=DEFAULT_MAX_MODELS):
        '''
        Initialize with the path to the models.yaml config file,
        the torch device type, and precision. The optional
        min_avail_mem argument specifies how much unused system
        (CPU) memory to preserve. The cache of models in RAM will
        grow until this value is approached. Default is 2G.
        '''
        # prevent nasty-looking CLIP log message
        transformers.logging.set_verbosity_error()
        self.config = config
        self.precision = precision
        self.device = torch.device(device_type)
        self.max_loaded_models = max_loaded_models
        self.models = {}
        self.stack = []  # this is an LRU FIFO
        self.current_model = None

    def valid_model(self, model_name:str)->bool:
        '''
        Given a model name, returns True if it is a valid
        identifier.
        '''
        return model_name in self.config

    def get_model(self, model_name:str):
        '''
        Given a model named identified in models.yaml, return
        the model object. If in RAM will load into GPU VRAM.
        If on disk, will load from there.
        '''
        if not self.valid_model(model_name):
            print(f'** "{model_name}" is not a known model name. Please check your models.yaml file')
            return self.current_model

        if self.current_model != model_name:
            if model_name not in self.models: # make room for a new one
                self._make_cache_room()
            self.offload_model(self.current_model)

        if model_name in self.models:
            requested_model = self.models[model_name]['model']
            print(f'>> Retrieving model {model_name} from system RAM cache')
            self.models[model_name]['model'] = self._model_from_cpu(requested_model)
            width = self.models[model_name]['width']
            height = self.models[model_name]['height']
            hash = self.models[model_name]['hash']

        else: # we're about to load a new model, so potentially offload the least recently used one
            try:
                requested_model, width, height, hash = self._load_model(model_name)
                self.models[model_name] = {
                    'model': requested_model,
                    'width': width,
                    'height': height,
                    'hash': hash,
                }

            except Exception as e:
                print(f'** model {model_name} could not be loaded: {str(e)}')
                traceback.print_exc()
                assert self.current_model,'** FATAL: no current model to restore to'
                print(f'** restoring {self.current_model}')
                self.get_model(self.current_model)
                return

        self.current_model = model_name
        self._push_newest_model(model_name)
        return {
            'model':requested_model,
            'width':width,
            'height':height,
            'hash': hash
        }

    def default_model(self) -> str | None:
        '''
        Returns the name of the default model, or None
        if none is defined.
        '''
        for model_name in self.config:
            if self.config[model_name].get('default'):
                return model_name

    def set_default_model(self,model_name:str) -> None:
        '''
        Set the default model. The change will not take
        effect until you call model_cache.commit()
        '''
        assert model_name in self.models,f"unknown model '{model_name}'"

        config = self.config
        for model in config:
            config[model].pop('default',None)
        config[model_name]['default'] = True

    def model_info(self, model_name:str)->dict:
        '''
        Given a model name returns the config object describing it.
        '''
        if model_name not in self.config:
            return None
        return self.config[model_name]

    def is_legacy(self,model_name:str)->bool:
        '''
        Return true if this is a legacy (.ckpt) model
        '''
        info = self.model_info(model_name)
        return info['format']=='ckpt' if info else False

    def list_models(self) -> dict:
        '''
        Return a dict of models in the format:
        { model_name1: {'status': ('active'|'cached'|'not loaded'),
                        'description': description,
                       },
          model_name2: { etc }
        '''
        models = {}
        for name in self.config:
            try:
                description = self.config[name].description
            except ConfigAttributeError:
                description = '<no description>'

            if self.current_model == name:
                status = 'active'
            elif name in self.models:
                status = 'cached'
            else:
                status = 'not loaded'

            models[name]={
                'status' : status,
                'description' : description
            }
        return models

    def print_models(self) -> None:
        '''
        Print a table of models, their descriptions, and load status
        '''
        models = self.list_models()
        for name in models:
            line = f'{name:25s} {models[name]["status"]:>10s}  {models[name]["description"]}'
            if models[name]['status'] == 'active':
                line = f'\033[1m{line}\033[0m'
            print(line)

    def del_model(self, model_name:str) -> None:
        '''
        Delete the named model.
        '''
        omega = self.config
        del omega[model_name]
        if model_name in self.stack:
            self.stack.remove(model_name)

    def add_model(self, model_name:str, model_attributes:dict, clobber:bool=False) -> None:
        '''
        Update the named model with a dictionary of attributes. Will fail with an
        assertion error if the name already exists. Pass clobber=True to overwrite.
        On a successful update, the config will be changed in memory and the
        method will return True. Will fail with an assertion error if provided
        attributes are incorrect or the model name is missing.
        '''
        omega = self.config
        assert 'format' in model_attributes, f'missing required field "format"'
        if model_attributes['format']=='diffusers':
            assert 'description' in model_attributes, 'required field "description" is missing'
            assert 'path' in model_attributes or 'repo_id' in model_attributes,'model must have either the "path" or "repo_id" fields defined'
        else:
            for field in ('description','weights','height','width','config'):
                assert field in model_attributes, f'required field {field} is missing'

        assert (clobber or model_name not in omega), f'attempt to overwrite existing model definition "{model_name}"'

        config = omega[model_name] if model_name in omega else {}
        for field in model_attributes:
            config[field] = model_attributes[field]

        omega[model_name] = config
        if clobber:
            self._invalidate_cached_model(model_name)

    def _load_model(self, model_name:str):
        """Load and initialize the model from configuration variables passed at object creation time"""
        if model_name not in self.config:
            print(f'"{model_name}" is not a known model name. Please check your models.yaml file')

        mconfig = self.config[model_name]

        # for usage statistics
        if self._has_cuda():
            torch.cuda.reset_peak_memory_stats()
            torch.cuda.empty_cache()

        tic = time.time()

        # this does the work
        model_format = mconfig.get('format', 'ckpt')
        if model_format == 'ckpt':
            weights = mconfig.weights
            print(f'>> Loading {model_name} from {weights}')
            model, width, height, model_hash = self._load_ckpt_model(model_name, mconfig)
        elif model_format == 'diffusers':
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                model, width, height, model_hash = self._load_diffusers_model(mconfig)
        else:
            raise NotImplementedError(f"Unknown model format {model_name}: {model_format}")

        # usage statistics
        toc = time.time()
        print(f'>> Model loaded in', '%4.2fs' % (toc - tic))
        if self._has_cuda():
            print(
                '>> Max VRAM used to load the model:',
                '%4.2fG' % (torch.cuda.max_memory_allocated() / 1e9),
                '\n>> Current VRAM usage:'
                '%4.2fG' % (torch.cuda.memory_allocated() / 1e9),
            )
        return model, width, height, model_hash

    def _load_ckpt_model(self, model_name, mconfig):
        config = mconfig.config
        weights = mconfig.weights
        vae = mconfig.get('vae')
        width = mconfig.width
        height = mconfig.height

        if not os.path.isabs(config):
            config = os.path.join(Globals.root,config)
        if not os.path.isabs(weights):
            weights = os.path.normpath(os.path.join(Globals.root,weights))
        # scan model
        self.scan_model(model_name, weights)

        print(f'>> Loading {model_name} from {weights}')

        # for usage statistics
        if self._has_cuda():
            torch.cuda.reset_peak_memory_stats()
            torch.cuda.empty_cache()

        tic = time.time()

        # this does the work
        if not os.path.isabs(config):
            config = os.path.join(Globals.root,config)
        omega_config = OmegaConf.load(config)
        with open(weights,'rb') as f:
            weight_bytes = f.read()
        model_hash = self._cached_sha256(weights, weight_bytes)
        sd = torch.load(io.BytesIO(weight_bytes), map_location='cpu')
        del weight_bytes
        # merged models from auto11 merge board are flat for some reason
        if 'state_dict' in sd:
            sd = sd['state_dict']

        print(f'  | Forcing garbage collection prior to loading new model')
        gc.collect()
        model = instantiate_from_config(omega_config.model)
        model.load_state_dict(sd, strict=False)

        if self.precision == 'float16':
            print('   | Using faster float16 precision')
            model.to(torch.float16)
        else:
            print('   | Using more accurate float32 precision')

        # look and load a matching vae file. Code borrowed from AUTOMATIC1111 modules/sd_models.py
        if vae:
            if not os.path.isabs(vae):
                vae = os.path.normpath(os.path.join(Globals.root,vae))
            if os.path.exists(vae):
                print(f'   | Loading VAE weights from: {vae}')
                vae_ckpt = torch.load(vae, map_location="cpu")
                vae_dict = {k: v for k, v in vae_ckpt["state_dict"].items() if k[0:4] != "loss"}
                model.first_stage_model.load_state_dict(vae_dict, strict=False)
            else:
                print(f'   | VAE file {vae} not found. Skipping.')

        model.to(self.device)
        # model.to doesn't change the cond_stage_model.device used to move the tokenizer output, so set it here
        model.cond_stage_model.device = self.device

        model.eval()

        for module in model.modules():
            if isinstance(module, (torch.nn.Conv2d, torch.nn.ConvTranspose2d)):
                module._orig_padding_mode = module.padding_mode

        # usage statistics
        toc = time.time()
        print(f'>> Model loaded in', '%4.2fs' % (toc - tic))

        if self._has_cuda():
            print(
                '>> Max VRAM used to load the model:',
                '%4.2fG' % (torch.cuda.max_memory_allocated() / 1e9),
                '\n>> Current VRAM usage:'
                '%4.2fG' % (torch.cuda.memory_allocated() / 1e9),
            )

        return model, width, height, model_hash

    def _load_diffusers_model(self, mconfig):
        name_or_path = self.model_name_or_path(mconfig)
        model_hash = 'FIXME'
        using_fp16 = self.precision == 'float16'

        print(f'>> Loading diffusers model from {name_or_path}')
        if using_fp16:
            print(f'  | Using faster float16 precision')
        else:
            print(f'  | Using more accurate float32 precision')

        # TODO: scan weights maybe?
        pipeline_args: dict[str, Any] = dict(
            safety_checker=None,
            local_files_only=not Globals.internet_available
        )
        if 'vae' in mconfig:
             vae = self._load_vae(mconfig['vae'])
             pipeline_args.update(vae=vae)
        if not isinstance(name_or_path,Path):
            pipeline_args.update(cache_dir=os.path.join(Globals.root,'models',name_or_path))
        if using_fp16:
            pipeline_args.update(torch_dtype=torch.float16)
            fp_args_list = [{'revision':'fp16'},{}]
        else:
            fp_args_list = [{}]

        verbosity = dlogging.get_verbosity()
        dlogging.set_verbosity_error()

        pipeline = None
        for fp_args in fp_args_list:
            try:
                pipeline = StableDiffusionGeneratorPipeline.from_pretrained(
                    name_or_path,
                    **pipeline_args,
                    **fp_args,
                )

            except OSError as e:
                if str(e).startswith('fp16 is not a valid'):
                    print(f'Could not fetch half-precision version of model {name_or_path}; fetching full-precision instead')
                else:
                    print(f'An unexpected error occurred while downloading the model: {e})')
            if pipeline:
                break

        dlogging.set_verbosity(verbosity)
        assert pipeline is not None, OSError(f'"{name_or_path}" could not be loaded')

        pipeline.to(self.device)

        # square images???
        width = pipeline.unet.config.sample_size * pipeline.vae_scale_factor
        height = width

        print(f'  | Default image dimensions = {width} x {height}')

        return pipeline, width, height, model_hash

    def model_name_or_path(self, model_name:Union[str,DictConfig]) -> str | Path:
        if isinstance(model_name,DictConfig):
            mconfig = model_name
        elif model_name in self.config:
            mconfig = self.config[model_name]
        else:
            raise ValueError(f'"{model_name}" is not a known model name. Please check your models.yaml file')

        if 'path' in mconfig:
            path = Path(mconfig['path'])
            if not path.is_absolute():
                path = Path(Globals.root, path).resolve()
            return path
        elif 'repo_id' in mconfig:
            return mconfig['repo_id']
        elif 'repo_name' in mconfig:
            return mconfig['repo_name']
        else:
            raise ValueError("Model config must specify either repo_id or path.")

    def offload_model(self, model_name:str) -> None:
        '''
        Offload the indicated model to CPU. Will call
        _make_cache_room() to free space if needed.
        '''
        if model_name not in self.models:
            return

        print(f'>> Offloading {model_name} to CPU')
        model = self.models[model_name]['model']
        self.models[model_name]['model'] = self._model_to_cpu(model)

        gc.collect()
        if self._has_cuda():
            torch.cuda.empty_cache()

    def scan_model(self, model_name, checkpoint):
        '''
        Apply picklescanner to the indicated checkpoint and issue a warning
        and option to exit if an infected file is identified.
        '''
        # scan model
        print(f'>> Scanning Model: {model_name}')
        scan_result = scan_file_path(checkpoint)
        if scan_result.infected_files != 0:
            if scan_result.infected_files == 1:
                print(f'\n### Issues Found In Model: {scan_result.issues_count}')
                print('### WARNING: The model you are trying to load seems to be infected.')
                print('### For your safety, InvokeAI will not load this model.')
                print('### Please use checkpoints from trusted sources.')
                print("### Exiting InvokeAI")
                sys.exit()
            else:
                print('\n### WARNING: InvokeAI was unable to scan the model you are using.')
                model_safe_check_fail = ask_user('Do you want to to continue loading the model?', ['y', 'n'])
                if model_safe_check_fail.lower() != 'y':
                    print("### Exiting InvokeAI")
                    sys.exit()
        else:
            print('>> Model scanned ok!')

    def autoconvert_weights(
            self,
            conf_path:Path,
            weights_directory:Path=None,
            dest_directory:Path=None,
    ):
        '''
        Scan the indicated directory for .ckpt files, convert into diffuser models,
        and import.
        '''
        weights_directory = weights_directory or global_autoscan_dir()
        dest_directory = dest_directory or Path(global_models_dir(), 'optimized-ckpts')

        print('>> Checking for unconverted .ckpt files in {weights_directory}')
        ckpt_files = dict()
        for root, dirs, files in os.walk(weights_directory):
            for f in files:
                if not f.endswith('.ckpt'):
                    continue
                basename = Path(f).stem
                dest = Path(dest_directory,basename)
                if not dest.exists():
                    ckpt_files[Path(root,f)]=dest

        if len(ckpt_files)==0:
            return

        print(f'>> New .ckpt file(s) found in {weights_directory}. Optimizing and importing...')
        for ckpt in ckpt_files:
            self.convert_and_import(ckpt, ckpt_files[ckpt])
        self.commit(conf_path)

    def convert_and_import(self, ckpt_path:Path, diffuser_path:Path)->dict:
        '''
        Convert a legacy ckpt weights file to diffuser model and import
        into models.yaml.
        '''
        from ldm.invoke.ckpt_to_diffuser import convert_ckpt_to_diffuser
        import transformers
        if diffuser_path.exists():
            print(f'ERROR: The path {str(diffuser_path)} already exists. Please move or remove it and try again.')
            return

        print(f'>> {ckpt_path.name}: optimizing (30-60s).')
        try:
            model_name = diffuser_path.name
            verbosity =transformers.logging.get_verbosity()
            transformers.logging.set_verbosity_error()
            convert_ckpt_to_diffuser(ckpt_path, diffuser_path)
            transformers.logging.set_verbosity(verbosity)
            print(f'>> Success. Optimized model is now located at {str(diffuser_path)}')
            print(f'>> Writing new config file entry for {model_name}...',end='')
            new_config = dict(
                path=str(diffuser_path),
                description=f'Optimized version of {model_name}',
                format='diffusers',
            )
            self.add_model(model_name, new_config, True)
            print('done.')
        except Exception as e:
            print(f'** Conversion failed: {str(e)}')
            traceback.print_exc()
        return new_config

    def del_config(self, model_name:str, gen, opt, completer):
        current_model = gen.model_name
        if model_name == current_model:
            print("** Can't delete active model. !switch to another model first. **")
            return
        gen.model_cache.del_model(model_name)
        gen.model_cache.commit(opt.conf)
        print(f'** {model_name} deleted')
        completer.del_model(model_name)

    def _make_cache_room(self) -> None:
        num_loaded_models = len(self.models)
        if num_loaded_models >= self.max_loaded_models:
            least_recent_model = self._pop_oldest_model()
            print(f'>> Cache limit (max={self.max_loaded_models}) reached. Purging {least_recent_model}')
            if least_recent_model is not None:
                del self.models[least_recent_model]
                gc.collect()

    def print_vram_usage(self) -> None:
        if self._has_cuda:
            print('>> Current VRAM usage: ','%4.2fG' % (torch.cuda.memory_allocated() / 1e9))

    def commit(self,config_file_path:str) -> None:
        '''
        Write current configuration out to the indicated file.
        '''
        yaml_str = OmegaConf.to_yaml(self.config)
        tmpfile = os.path.join(os.path.dirname(config_file_path),'new_config.tmp')
        with open(tmpfile, 'w') as outfile:
            outfile.write(self.preamble())
            outfile.write(yaml_str)
        os.replace(tmpfile,config_file_path)

    def preamble(self) -> str:
        '''
        Returns the preamble for the config file.
        '''
        return textwrap.dedent('''\
            # This file describes the alternative machine learning models
            # available to InvokeAI script.
            #
            # To add a new model, follow the examples below. Each
            # model requires a model config file, a weights file,
            # and the width and height of the images it
            # was trained on.
        ''')

    def _invalidate_cached_model(self,model_name:str) -> None:
        self.offload_model(model_name)
        if model_name in self.stack:
            self.stack.remove(model_name)
        self.models.pop(model_name,None)

    def _model_to_cpu(self,model):
        if self.device == 'cpu':
            return model

        # diffusers really really doesn't like us moving a float16 model onto CPU
        import logging
        logging.getLogger('diffusers.pipeline_utils').setLevel(logging.CRITICAL)
        model.cond_stage_model.device = 'cpu'
        model.to('cpu')
        logging.getLogger('pipeline_utils').setLevel(logging.INFO)

        for submodel in ('first_stage_model','cond_stage_model','model'):
            try:
                getattr(model,submodel).to('cpu')
            except AttributeError:
                pass
        return model

    def _model_from_cpu(self,model):
        if self.device == 'cpu':
            return model

        model.to(self.device)
        model.cond_stage_model.device = self.device

        for submodel in ('first_stage_model','cond_stage_model','model'):
            try:
                getattr(model,submodel).to(self.device)
            except AttributeError:
                pass

        return model

    def _pop_oldest_model(self):
        '''
        Remove the first element of the FIFO, which ought
        to be the least recently accessed model. Do not
        pop the last one, because it is in active use!
        '''
        return self.stack.pop(0)

    def _push_newest_model(self,model_name:str) -> None:
        '''
        Maintain a simple FIFO. First element is always the
        least recent, and last element is always the most recent.
        '''
        with contextlib.suppress(ValueError):
            self.stack.remove(model_name)
        self.stack.append(model_name)

    def _has_cuda(self) -> bool:
        return self.device.type == 'cuda'

    def _cached_sha256(self,path,data) -> Union[str, bytes]:
        dirname    = os.path.dirname(path)
        basename   = os.path.basename(path)
        base, _    = os.path.splitext(basename)
        hashpath   = os.path.join(dirname,base+'.sha256')

        if os.path.exists(hashpath) and os.path.getmtime(path) <= os.path.getmtime(hashpath):
            with open(hashpath) as f:
                hash = f.read()
            return hash

        print(f'>> Calculating sha256 hash of weights file')
        tic = time.time()
        sha = hashlib.sha256()
        sha.update(data)
        hash = sha.hexdigest()
        toc = time.time()
        print(f'>> sha256 = {hash}','(%4.2fs)' % (toc - tic))

        with open(hashpath,'w') as f:
            f.write(hash)
        return hash

    def _load_vae(self, vae_config):
        vae_args = {}
        name_or_path = self.model_name_or_path(vae_config)
        using_fp16 = self.precision == 'float16'

        vae_args.update(
            cache_dir=os.path.join(Globals.root,'models',name_or_path),
            local_files_only=not Globals.internet_available,
        )

        print(f'  | Loading diffusers VAE from {name_or_path}')
        if using_fp16:
            vae_args.update(torch_dtype=torch.float16)
            fp_args_list = [{'revision':'fp16'},{}]
        else:
            print(f'  | Using more accurate float32 precision')
            fp_args_list = [{}]

        vae = None
        deferred_error = None

        for fp_args in fp_args_list:
            # At some point we might need to be able to use different classes here? But for now I think
            # all Stable Diffusion VAE are AutoencoderKL.
            try:
                vae = AutoencoderKL.from_pretrained(name_or_path, **vae_args, **fp_args)
            except OSError as e:
                if str(e).startswith('fp16 is not a valid'):
                    print(f'  | Half-precision version of model not available; fetching full-precision instead')
                else:
                    deferred_error = e
            if vae:
                break

        if not vae and deferred_error:
            print(f'** Could not load VAE {name_or_path}: {str(deferred_error)}')

        # comment by lstein: I don't know what this does
        if 'subfolder' in vae_config:
            vae_args['subfolder'] = vae_config['subfolder']

        return vae
