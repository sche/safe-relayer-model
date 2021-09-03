from models import Base, Block
from database import database as db


def main():
    Base.metadata.create_all(db.engine)


if __name__ == '__main__':
    main()
