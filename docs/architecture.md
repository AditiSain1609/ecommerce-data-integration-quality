# Architecture

Files enter through `src.extract`; pandas frames form the transient staging layer. `src.transform` standardizes and rejects row-level defects. `src.data_integration` checks foreign keys. `src.load` persists clean entities transactionally and stores rejected payloads/issues. `src.pipeline` records run lifecycle and quality summaries. Flask serves database-derived pages and a compact JSON metric endpoint.

The database URL selects local SQLite by default or MySQL via `mysql+pymysql`. All SQL values are bound parameters. The pipeline writes each load transaction atomically; run metadata is separately updated to failed if a critical stage raises.
