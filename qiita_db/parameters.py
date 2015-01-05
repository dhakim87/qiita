# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The Qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------
from __future__ import division

from .base import QiitaObject
from .sql_connection import SQLConnectionHandler
from .util import get_table_cols_w_type, get_table_cols
from .exceptions import QiitaDBDuplicateError


class BaseParameters(QiitaObject):
    r"""Base object to access to the parameters table"""

    @classmethod
    def _check_columns(cls, **kwargs):
        db_cols = set(get_table_cols(cls._table))
        db_cols.remove("param_set_name")
        db_cols.remove("preprocessed_params_id")
        missing = db_cols.difference(kwargs)

        if missing:
            raise ValueError("Missing columns: %s" % ', '.join(missing))

        extra = set(kwargs).difference(db_cols)
        if extra:
            raise ValueError("Extra columns: %s" % ', '.join(extra))

    @classmethod
    def exists(cls, **kwargs):
        r"""Check if the parameter set already exists on the DB"""
        cls._check_columns(**kwargs)

        conn_handler = SQLConnectionHandler()

        cols = ["{} = %s".format(col) for col in kwargs]

        return conn_handler.execute_fetchone(
            "SELECT EXISTS(SELECT * FROM qiita.{0} WHERE {1})".format(
                cls._table, ' AND '.join(cols)),
            kwargs.values())[0]

    @classmethod
    def create(cls, param_set_name, **kwargs):
        r"""Adds a new parameter set to the DB"""
        cls._check_columns(**kwargs)

        conn_handler = SQLConnectionHandler()

        vals = kwargs.values()
        vals.insert(0, param_set_name)

        if cls.exists(**kwargs):
            raise QiitaDBDuplicateError(cls.__name__, "Values: %s" % kwargs)

        id_ = conn_handler.execute_fetchone(
            "INSERT INTO qiita.{0} (param_set_name, {1}) VALUES (%s, {2}) "
            "RETURNING preprocessed_params_id".format(
                cls._table, ', '.join(kwargs),
                ', '.join(['%s'] * len(kwargs))),
            vals)[0]

        return cls(id_)

    def _check_id(self, id_, conn_handler=None):
        r"""Check that the provided ID actually exists in the database

        Parameters
        ----------
        id_ : object
            The ID to test
        conn_handler : SQLConnectionHandler
            The connection handler object connected to the DB

        Notes
        -----
        This function overwrites the base function, as sql layout doesn't
        follow the same conventions done in the other classes.
        """
        self._check_subclass()

        conn_handler = (conn_handler if conn_handler is not None
                        else SQLConnectionHandler())
        return conn_handler.execute_fetchone(
            "SELECT EXISTS(SELECT * FROM qiita.{0} WHERE {1} = %s)".format(
                self._table, self._column_id),
            (id_, ))[0]

    def _get_values_as_dict(self, conn_handler):
        r""""""
        return dict(conn_handler.execute_fetchone(
                    "SELECT * FROM qiita.{0} WHERE {1}=%s".format(
                        self._table, self._column_id), (self.id,)))

    def to_str(self):
        r"""Generates a string with the parameter values

        Returns
        -------
        str
            The string with all the parameters
        """
        conn_handler = SQLConnectionHandler()
        table_cols = get_table_cols_w_type(self._table)
        table_cols.remove([self._column_id, 'bigint'])

        values = self._get_values_as_dict(conn_handler=conn_handler)

        result = []
        for p_name, p_type in sorted(table_cols):
            if p_name in self._ignore_cols:
                continue
            if p_type == 'boolean':
                if values[p_name]:
                    result.append("--%s" % p_name)
            else:
                result.append("--%s %s" % (p_name, values[p_name]))

        return " ".join(result)


class PreprocessedIlluminaParams(BaseParameters):
    r"""Gives access to the preprocessed parameters of illumina data"""

    _column_id = "preprocessed_params_id"
    _table = "preprocessed_sequence_illumina_params"
    _ignore_cols = {"param_set_name"}


class Preprocessed454Params(BaseParameters):
    r"""Gives access to the preprocessed parameters of illumina data"""

    _column_id = "preprocessed_params_id"
    _table = "preprocessed_sequence_454_params"
    _ignore_cols = {"param_set_name"}


class ProcessedSortmernaParams(BaseParameters):
    r"""Gives access to the processed parameters using SortMeRNA"""

    _column_id = "processed_params_id"
    _table = "processed_params_sortmerna"
    _ignore_cols = {'reference_id'}

    @property
    def reference(self):
        """"Returns the reference id used on this parameter set"""
        conn_handler = SQLConnectionHandler()

        return conn_handler.execute_fetchone(
            "SELECT reference_id FROM qiita.{0} WHERE {1}=%s".format(
                self._table, self._column_id), (self.id,))[0]

    def to_file(self, f):
        r"""Writes the parameters to a file in QIIME parameters file format

        Parameters
        ----------
        f : file-like object
            File-like object to write the parameters. Should support the write
            operation
        """
        conn_handler = SQLConnectionHandler()
        values = self._get_values_as_dict(conn_handler)

        # Remove the id column
        del values[self._column_id]

        # We know that the execution method is SortMeRNA,
        # add it to the parameter file
        f.write("pick_otus:otu_picking_method\tsortmerna\n")

        for key, value in sorted(values.items()):
            if key in self._ignore_cols:
                continue
            f.write("pick_otus:%s\t%s\n" % (key, value))
