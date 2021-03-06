# Copyright 2017-2018, The Johns Hopkins University Applied Physics Laboratory LLC
# All rights reserved.
# Distributed under the terms of the Apache 2.0 License.

import os
import json
import csv


class TranslationDictManager(object):
    """
    Translation dictionary manager

    Format of dictionary is a dictionary of lists.
    The key of the dictionary is the source string.
    Each list has two entries: translation string and entity type.
    """
    ENTITY_TYPES = ["PER", 'ORG', 'GPE', 'LOC', 'NONE']

    def __init__(self, base_dir):
        self.base_dir = base_dir

    def add(self, lang, source, translation, type):
        source = source.lower()
        type = type.upper()
        if type not in self.ENTITY_TYPES:
            type = self._guess_type(type)
        trans_dict = self.get(lang)
        trans_dict[source] = [translation, type]
        self.save(lang, trans_dict)

    def merge(self, lang, td):
        trans_dict = self.get(lang)
        for key in td:
            trans_dict[key] = td[key]

    def get(self, lang):
        trans_dict = {}
        filename = self.get_filename(lang)
        if os.path.exists(filename):
            with open(filename, 'r') as fp:
                trans_dict = json.load(fp)
        return trans_dict

    def save(self, lang, td):
        filename = self.get_filename(lang)
        with open(filename, 'w') as fp:
            json.dump(td, fp)

    def get_filename(self, lang):
        lang = lang.lower()
        return os.path.join(self.base_dir, lang + '.json')

    def export(self, lang, filename):
        trans_dict = self.get(lang)
        count = 0
        with open(filename, 'w') as fp:
            for source in trans_dict.keys():
                count += 1
                fp.write("{}\t{}\t{}\n".format(source, *trans_dict[source]))
        return count

    def import_(self, lang, filename):
        trans_dict = self.get(lang)
        count = 0
        with open(filename, 'r') as fp:
            reader = csv.reader(fp, delimiter='\t', quoting=csv.QUOTE_NONE)
            for row in reader:
                if len(row) != 3:
                    print("Warning: row without 3 columns")
                    continue
                if row[0] not in trans_dict:
                    count += 1
                    trans_dict[row[0]] = [row[1], row[2]]
        self.save(lang, trans_dict)
        return count

    def _guess_type(self, type):
        if type == 'P':
            return 'PER'
        elif type == 'O':
            return 'ORG'
        elif type == 'G':
            return 'GPE'
        elif type == 'L':
            return 'LOC'
        elif type == 'N':
            return 'NONE'

        distances = list(map(lambda x: self._get_hamming_distance(x, type), self.ENTITY_TYPES))
        return self.ENTITY_TYPES[distances.index(min(distances))]

    @staticmethod
    def _get_hamming_distance(s1, s2):
        s1 = s1.ljust(max(len(s1), len(s2)))
        s2 = s2.ljust(max(len(s1), len(s2)))
        return sum(map(str.__ne__, s1, s2))
