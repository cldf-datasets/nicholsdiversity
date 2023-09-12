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


def make_language(row, languoids, glottocode_map):
    lang = {
        'ID': row['ID'],
        'Name': row['Name'],
    }
    if row.get('Lat') and row.get('Lon'):
        row['Latitude'] = row['Lat']
        row['Longitude'] = row['Lon']

    glottocode = glottocode_map.get(row['ID'])
    if glottocode:
        languoid = languoids.get(glottocode)
        lang['Glottocode'] = glottocode
        lang['Macroarea'] = languoid.macroareas[0].name
        if languoid.iso_code:
            lang['ISO639P3code'] = languoid.iso_code
        if languoid.latitude and languoid.longitude:
            lang['Latitude'] = languoid.latitude
            lang['Longitude'] = languoid.longitude

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

        glottocode_map = {
            lang['ID']: lang['Glottocode']
            for lang in self.etc_dir.read_csv('glottocodes.csv', dicts=True)
            if re.fullmatch('[a-z]{4}[0-9]{4}', lang.get('Glottocode', ''))}

        parameter_table = self.etc_dir.read_csv('parameters.csv', dicts=True)
        code_table = self.etc_dir.read_csv('codes.csv', dicts=True)

        languoids = {
            l.id: l
            for l in args.glottolog.api.languoids(ids=glottocode_map.values())}

        # process

        language_table = [
            make_language(row, languoids, glottocode_map)
            for row in raw_data]

        param_ids = [param['ID'] for param in parameter_table]
        code_index = {
            (code['Parameter_ID'], code['Old_Name']): code['ID']
            for code in code_table}
        value_table = [
            {
                'ID': '{}-{}'.format(row['ID'], param_id),
                'Language_ID': row['ID'],
                'Parameter_ID': param_id,
                'Code_ID': code_index.get((param_id, row[param_id])) or '',
                'Value': row[param_id],
            }
            for row in raw_data
            for param_id in param_ids
            if row.get(param_id)]

        # schema

        args.writer.cldf.add_component('LanguageTable')
        args.writer.cldf.add_component('ParameterTable')
        args.writer.cldf.add_component('CodeTable')

        # write cldf

        args.writer.objects['LanguageTable'] = language_table
        args.writer.objects['ParameterTable'] = parameter_table
        args.writer.objects['CodeTable'] = code_table
        args.writer.objects['ValueTable'] = value_table
