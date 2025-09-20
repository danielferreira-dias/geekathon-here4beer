from db import engine
from models import *  # noqa: F401,F403
from db import Base


def main():
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized.")


if __name__ == "__main__":
    main()
