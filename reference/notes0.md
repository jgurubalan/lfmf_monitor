                    ┌─────────────────┐
                    │  configuration  │
                    │  receiver.yaml  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │     main.py     │
                    │  Orchestrator   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │     rtl.py      │
                    │  RTL-SDR input  │
                    └────────┬────────┘
                             │
                             ▼
                       RTL-SDR V4
                             │
                             ▼
                         I/Q samples
                             │
                 ┌───────────┴───────────┐
                 ▼                       ▼
          ┌─────────────┐         ┌─────────────┐
          │  buffer.py  │         │ spectrum.py │
          │ sample data │         │     FFT     │
          └─────────────┘         └──────┬──────┘
                                         │
                                         ▼
                                  spectrum data
                                         │
                              ┌──────────┴──────────┐
                              ▼                     ▼
                       data/spectrum/         transport.py
                                             server/network