"""Throwaway probe: a domain module that breaks R1 by importing SQLAlchemy."""

import sqlalchemy

METADATA = sqlalchemy.MetaData()
