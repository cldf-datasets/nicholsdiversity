import csv
import pathlib
import re

from cldfbench import CLDFSpec, Dataset as BaseDataset


def read_raw_csv(f):
    # skip that first line that just says 'Table 1'
    _ = next(f)
    reader = csv.reader(f, delimiter=';')
    header = [k.strip() for k in next(reader)]
    # skip parameter names (I already copied them to etc/)
    _ = next(reader)
    return [
        {k: v.strip() for k, v in zip(header, row) if v.strip()}
        for row in reader]


def make_language(row, languoids, etc_languages):
    lang = {
        'ID': row['ID'],
        'Name': row['Name'],
    }
    if row.get('Lat') and row.get('Lon'):
        row['Latitude'] = row['Lat']
        row['Longitude'] = row['Lon']

    etc_language = etc_languages.get(row['ID']) or {}
    if (glottocode := etc_language.get('Glottocode')):
        languoid = languoids.get(glottocode)
        lang['Glottocode'] = glottocode
        if languoid.macroareas:
            lang['Macroarea'] = languoid.macroareas[0].name
        if languoid.iso_code:
            lang['ISO639P3code'] = languoid.iso_code
        if languoid.latitude and languoid.longitude:
            lang['Latitude'] = languoid.latitude
            lang['Longitude'] = languoid.longitude
    if (sources := etc_language.get('Source')):
        lang['Source'] = [
            trimmed
            for src in sources.split(';')
            if (trimmed := src.strip())]

    return lang


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "nicholsdiversity"

    def cldf_specs(self):  # A dataset must declare all CLDF sets it creates.
        return CLDFSpec(
            dir=self.cldf_dir,
            module='StructureDataset',
            metadata_fname='cldf-metadata.json')

    def cmd_download(self, args):
        """
        Download files to the raw/ directory. You can use helpers methods of `self.raw_dir`, e.g.

        >>> self.raw_dir.download(url, fname)
        """
        pass

    def cmd_makecldf(self, args):
        """
        Convert the raw data to a CLDF dataset.

        >>> args.writer.objects['LanguageTable'].append(...)
        """
        # read data

        data_file = self.raw_dir / 'Nichols1992_with_Pnames.csv'
        with open(data_file, encoding='utf-8') as f:
            raw_data = read_raw_csv(f)
        sources = self.etc_dir.read_bib('sources.bib')

        etc_languages = {
            lang['ID']: lang
            for lang in self.etc_dir.read_csv('languages.csv', dicts=True)}

        parameter_table = self.etc_dir.read_csv('parameters.csv', dicts=True)
        code_table = {
            (code['Parameter_ID'], code['Old_Name']): code
            for code in self.etc_dir.read_csv('codes.csv', dicts=True)}

        glottocodes = {lg['Glottocode'] for lg in etc_languages.values()}
        languoids = {
            l.id: l for l in args.glottolog.api.languoids(ids=glottocodes)}

        # process

        language_table = [
            make_language(row, languoids, etc_languages)
            for row in raw_data]

        param_ids = [param['ID'] for param in parameter_table]

        def _code(param_id, old_value):
            return code_table.get((param_id, old_value)) or {}

        value_table = [
            {
                'ID': '{}-{}'.format(row['ID'], param_id),
                'Language_ID': row['ID'],
                'Parameter_ID': param_id,
                'Code_ID': (code := _code(param_id, row[param_id])).get('ID') or '',
                'Value': code.get('Name') or row[param_id],
            }
            for row in raw_data
            for param_id in param_ids
            if row.get(param_id)]

        # schema

        args.writer.cldf.add_component(
            'LanguageTable',
            {
                'dc:extent': 'multivalued',
                'name': 'Source',
                'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#source',
                'separator': ';',
            })
        args.writer.cldf.add_component('ParameterTable')
        args.writer.cldf.add_component('CodeTable', 'Map_Icon')

        # write cldf

        args.writer.objects['LanguageTable'] = language_table
        args.writer.objects['ParameterTable'] = parameter_table
        args.writer.objects['CodeTable'] = code_table.values()
        args.writer.objects['ValueTable'] = value_table
        args.writer.cldf.add_sources(*sources)
