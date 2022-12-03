# Copyright (c) 2022 Kyle Schouviller (https://github.com/kyle0654)

import os
import sys
import traceback

from ..services.image_storage import DiskImageStorage
from ..services.session_manager import DiskSessionManager
from ..services.invocation_queue import MemoryInvocationQueue
from ..services.invocation_services import InvocationServices
from ..services.invoker import Invoker, InvokerServices
from ....generate import Generate
from .events import FastAPIEventService


class ApiDependencies:
    """Contains and initializes all dependencies for the API"""
    invoker: Invoker = None

    @staticmethod
    def initialize(
        args,
        config,
        event_handler_id: int
        ):

        # TODO: this initialization is getting large (for Generate at least) - can this be more modular?
        # Loading Face Restoration and ESRGAN Modules

        # TODO: Remove the need for globals
        from ldm.invoke.globals import Globals

        # alert - setting globals here
        Globals.root = os.path.expanduser(args.root_dir or os.environ.get('INVOKEAI_ROOT') or os.path.abspath('.'))
        Globals.try_patchmatch = args.patchmatch
        
        print(f'>> InvokeAI runtime directory is "{Globals.root}"')

        # these two lines prevent a horrible warning message from appearing
        # when the frozen CLIP tokenizer is imported
        import transformers
        transformers.logging.set_verbosity_error()

        # Loading Face Restoration and ESRGAN Modules
        gfpgan, codeformer, esrgan = None, None, None
        try:
            if config.restore or config.esrgan:
                from ldm.invoke.restoration import Restoration
                restoration = Restoration()
                if config.restore:
                    gfpgan, codeformer = restoration.load_face_restore_models(config.gfpgan_model_path)
                else:
                    print('>> Face restoration disabled')
                if config.esrgan:
                    esrgan = restoration.load_esrgan(config.esrgan_bg_tile)
                else:
                    print('>> Upscaling disabled')
            else:
                print('>> Face restoration and upscaling disabled')
        except (ModuleNotFoundError, ImportError):
            print(traceback.format_exc(), file=sys.stderr)
            print('>> You may need to install the ESRGAN and/or GFPGAN modules')

        # normalize the config directory relative to root
        if not os.path.isabs(config.conf):
            config.conf = os.path.normpath(os.path.join(Globals.root,config.conf))

        if config.embeddings:
            if not os.path.isabs(config.embedding_path):
                embedding_path = os.path.normpath(os.path.join(Globals.root,config.embedding_path))
        else:
            embedding_path = None


        # TODO: lazy-initialize this by wrapping it
        try:
            generate = Generate(
                conf              = config.conf,
                model             = config.model,
                sampler_name      = config.sampler_name,
                embedding_path    = embedding_path,
                full_precision    = config.full_precision,
                precision         = config.precision,
                gfpgan            = gfpgan,
                codeformer        = codeformer,
                esrgan            = esrgan,
                free_gpu_mem      = config.free_gpu_mem,
                safety_checker    = config.safety_checker,
                max_loaded_models = config.max_loaded_models,
            )
        except (FileNotFoundError, TypeError, AssertionError):
            #emergency_model_reconfigure() # TODO?
            sys.exit(-1)
        except (IOError, KeyError) as e:
            print(f'{e}. Aborting.')
            sys.exit(-1)

        generate.free_gpu_mem = config.free_gpu_mem

        events = FastAPIEventService(event_handler_id)

        output_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../outputs'))

        images = DiskImageStorage(output_folder)

        services = InvocationServices(
            generate = generate,
            events   = events,
            images   = images
        )

        invoker_services = InvokerServices(
            queue = MemoryInvocationQueue(),
            session_manager = DiskSessionManager(output_folder)
        )

        ApiDependencies.invoker = Invoker(services, invoker_services)
    
    @staticmethod
    def shutdown():
        if ApiDependencies.invoker:
            ApiDependencies.invoker.stop()
