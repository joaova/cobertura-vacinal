"""Permite executar:  python -m vacina_sarampo.etl"""
import sys

from .carga import main

sys.exit(main())
