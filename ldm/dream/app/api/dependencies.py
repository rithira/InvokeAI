# Copyright (c) 2022 Kyle Schouviller (https://github.com/kyle0654)

import os

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
        config,
        event_handler_id: int
        ):
        # TODO: lazy-initialize this by wrapping it
        generate = Generate(
            model=config.model,
            sampler_name=config.sampler_name,
            embedding_path=config.embedding_path,
            full_precision=config.full_precision,
        )
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