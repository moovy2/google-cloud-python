
transport inheritance structure
_______________________________

`InternalRangeServiceTransport` is the ABC for all transports.
- public child `InternalRangeServiceGrpcTransport` for sync gRPC transport (defined in `grpc.py`).
- public child `InternalRangeServiceGrpcAsyncIOTransport` for async gRPC transport (defined in `grpc_asyncio.py`).
- private child `_BaseInternalRangeServiceRestTransport` for base REST transport with inner classes `_BaseMETHOD` (defined in `rest_base.py`).
- public child `InternalRangeServiceRestTransport` for sync REST transport with inner classes `METHOD` derived from the parent's corresponding `_BaseMETHOD` classes (defined in `rest.py`).
