# -----------------------------------------------------------------------------
# Copyright (c) 2014--, The Qiita Development Team.
#
# Distributed under the terms of the BSD 3-clause License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------

from operator import itemgetter

from future.utils import viewitems
from wtforms import Form, BooleanField

from qiita_db.util import (get_filetypes, get_files_from_uploads_folders,
                           get_data_types, convert_to_id, get_filepath_types)
from qiita_db.study import Study
from qiita_db.data import RawData
from qiita_db.user import User
from qiita_db.ontology import Ontology
from qiita_db.metadata_template import PrepTemplate
from .base_uimodule import BaseUIModule


def get_raw_data_from_other_studies(user, study):
    """Retrieves a tuple of raw_data_id and the last study title for that
    raw_data
    """
    d = {}
    for sid in user.user_studies:
        if sid == study.id:
            continue
        for rdid in Study(sid).raw_data():
            d[int(rdid)] = Study(RawData(rdid).studies[-1]).title
    return d


def get_raw_data(rdis):
    """Get all raw data objects from a list of raw_data_ids"""
    return [RawData(rdi) for rdi in rdis]


class PreprocessParametersForm(Form):
    r"""WTForm for introducing the preprocessing parameters

    Allows editing the split_libraries_fastq.py parameters

    Attributes
    ----------
    rev_comp_mapping_barcodes

    See Also
    --------
    wtforms.Form
    """
    rev_comp_mapping_barcodes = BooleanField("rev_comp_mapping_barcodes")


class RawDataTab(BaseUIModule):
    def render(self, study):
        user = User(self.current_user)

        filetypes = sorted(viewitems(get_filetypes()), key=itemgetter(1))
        other_studies_rd = sorted(viewitems(
            get_raw_data_from_other_studies(user, study)))

        raw_data_info = [(rd.id, rd.filetype, rd)
                         for rd in get_raw_data(study.raw_data())]

        return self.render_string(
            "raw_data_tab.html",
            filetypes=filetypes,
            other_studies_rd=other_studies_rd,
            available_raw_data=raw_data_info,
            study=study)


class RawDataEditorTab(BaseUIModule):
    def render(self, study, raw_data):
        user = User(self.current_user)
        study_status = study.status
        user_level = user.level
        raw_data_id = raw_data.id
        files = get_files_from_uploads_folders(str(study.id))

        # Get the available prep template data types
        data_types = sorted(viewitems(get_data_types()), key=itemgetter(1))

        # Get all the ENA terms for the investigation type
        ontology = Ontology(convert_to_id('ENA', 'ontology'))
        # make "Other" show at the bottom of the drop down menu
        ena_terms = []
        for v in sorted(ontology.terms):
            if v != 'Other':
                ena_terms.append('<option value="%s">%s</option>' % (v, v))
        ena_terms.append('<option value="Other">Other</option>')

        # New Type is for users to add a new user-defined investigation type
        user_defined_terms = ontology.user_defined_terms + ['New Type']

        # Get all the information about the prep templates
        available_prep_templates = [PrepTemplate(p)
                                    for p in sorted(raw_data.prep_templates)
                                    if PrepTemplate.exists(p)]

        # getting filepath_types
        fts = [k.split('_', 1)[1].replace('_', ' ')
               for k in get_filepath_types() if k.startswith('raw_')]

        # The raw data can be edited (e.i. adding prep templates and files)
        # only if the study is sandboxed or the current user is an admin
        is_editable = study_status == 'sandbox' or user_level == 'admin'

        # Get the files linked with the raw_data
        raw_data_files = raw_data.get_filepaths()

        # Get the status of the data linking
        raw_data_link_status = raw_data.link_filepaths_status

        # By default don't show the unlink button
        show_unlink_btn = False
        # By default disable the the link file button
        disable_link_btn = True
        # Define the message for the link status
        if raw_data_link_status == 'linking':
            link_msg = "Linking files..."
        elif raw_data_link_status == 'unlinking':
            link_msg = "Unlinking files..."
        else:
            # The link button is only disable if raw data link status is
            # linking or unlinking, so we can enable it here
            disable_link_btn = False
            # The unlink button is only shown if the study is editable, the raw
            # data linking status is not in linking or unlinking, and there are
            # files attached to the raw data. At this  point, we are sure that
            # the raw data linking status is not in linking or unlinking so we
            # still need to check if it is editable or there are files attached
            show_unlink_btn = is_editable and raw_data_files
            if raw_data_link_status.startswith('failed'):
                link_msg = "Error (un)linkingfiles: %s" % raw_data_link_status
            else:
                link_msg = ""

        # Get the raw_data filetype
        raw_data_filetype = raw_data.filetype

        return self.render_string(
            "raw_data_editor_tab.html",
            study_id=study.id,
            study_status=study_status,
            user_level=user_level,
            raw_data_id=raw_data_id,
            files=files,
            data_types=data_types,
            ena_terms=ena_terms,
            user_defined_terms=user_defined_terms,
            available_prep_templates=available_prep_templates,
            filepath_types=fts,
            is_editable=is_editable,
            show_unlink_btn=show_unlink_btn,
            link_msg=link_msg,
            raw_data_files=raw_data_files,
            raw_data_filetype=raw_data_filetype,
            disable_link_btn=disable_link_btn)


class PrepTemplatePanel(BaseUIModule):
    def render(self, prep, study_id, is_editable, ena_terms,
               study_status, user_defined_terms):
        # Check if the request came from a local source
        is_local_request = self._is_local()

        prep_id = prep.id
        data_type = prep.data_type()
        filepaths = prep.get_filepaths()
        investigation_type = prep.investigation_type
        preprocessed_data = prep.preprocessed_data
        preprocessing_status = prep.preprocessing_status
        preprocess_form = PreprocessParametersForm()

        return self.render_string(
            "prep_template_panel.html",
            prep_id=prep_id,
            data_type=data_type,
            filepaths=filepaths,
            investigation_type=investigation_type,
            preprocessed_data=preprocessed_data,
            preprocessing_status=preprocessing_status,
            study_id=study_id,
            is_local_request=is_local_request,
            is_editable=is_editable,
            ena_terms=ena_terms,
            study_status=study_status,
            user_defined_terms=user_defined_terms,
            preprocess_form=preprocess_form)
