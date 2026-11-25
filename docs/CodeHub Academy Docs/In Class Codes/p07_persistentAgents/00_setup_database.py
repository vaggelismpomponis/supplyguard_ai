"""
Run once before database lessons; rerunning applies pending migrations.

uv add --upgrade langgraph-checkpoint-postgres "psycopg[binary,pool]"

"""
print("Loading imports...", flush=True)

from psycopg.conninfo import make_conninfo
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore
from p07_persistentAgents.common import database_url

if __name__ == "__main__":
    print("Reading database URL...", flush=True)
    db_uri = make_conninfo(
            database_url(),
            connect_timeout=10,
            options="-c statement_timeout=30000 -c lock_timeout=10000",
        )

    print("Connecting saver...", flush=True)
    with PostgresSaver.from_conn_string(db_uri) as saver:
        print("Starting saver.setup()...", flush=True)
        saver.setup()
        print("Saver setup completed.", flush=True)

    print("Connecting store...", flush=True)
    with PostgresStore.from_conn_string(db_uri) as store:
        print("Starting store.setup()...", flush=True)
        store.setup()
        print("Store setup completed.", flush=True)

    print("Checkpoint and Store tables are ready.", flush=True)