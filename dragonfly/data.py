# Copyright 2017-2018, The Johns Hopkins University Applied Physics Laboratory LLC
# All rights reserved.
# Distributed under the terms of the Apache 2.0 License.

import csv
import os
import glob


class FileLister(object):
    """
    Get the name of a file to annotate
    """
    def __init__(self, input, file_ext):
        self.path = input
        if os.path.isdir(input):
            self.is_dir = True
            pattern = '*' + file_ext
            self.filenames = [x for x in glob.glob(os.path.join(input, pattern)) if os.path.isfile(x)]
            self.filenames = sorted(self.filenames)
        else:
            self.is_dir = False
            self.filenames = [input]

    def get_filename(self, index):
        if index < len(self.filenames):
            return self.filenames[index]

    def get_index_from_filename(self, filename):
        if filename in self.filenames:
            return self.filenames.index(filename)
        for index in enumerate(self.filenames):
            if filename in self.filenames[index[0]]:
                return index[0]
        return None

    def has_next(self, index):
        return (index + 1) < len(self.filenames)

    def __contains__(self, key):
        return 0 <= key < len(self.filenames)


class AnnotationLoader(object):
    def __init__(self, path):
        self.base = path

    def get(self, filename):
        filename = os.path.basename(filename)
        annotation_filename = filename + '.anno'
        path = os.path.join(self.base, annotation_filename)
        if os.path.isfile(path):
            return path


class HintLoader(object):
    def __init__(self, path):
        self.hints = []
        with open(path, 'r') as fp:
            reader = csv.reader(fp, delimiter='\t', quoting=csv.QUOTE_NONE)
            for row in reader:
                self.hints.append({'regex': row[0], 'comment': row[1]})


class TranslationLoader(object):
    def __init__(self, path):
        self.base = path

    def get(self, filename):
        filename = os.path.basename(filename)
        translation_filename = filename + '.eng'
        path = os.path.join(self.base, translation_filename)
        if os.path.isfile(path):
            with open(path, 'r') as ifp:
                return [x for x in ifp]


class CompressionModelLoader(object):
    def __init__(self, path):
        self.base = path

    def get(self, filename):
        filename = os.path.basename(filename)
        filename = filename.replace('.conll.txt', '')
        translation_filename = filename + '.cm'
        path = os.path.join(self.base, translation_filename)
        if os.path.isfile(path):
            with open(path, 'r') as ifp:
                return [x for x in ifp]


class Document(object):
    """
    Contains a list of sentences and optional annotations
    """
    def __init__(self, filename, sentences):
        self.filename = filename
        self.sentences = sentences
        self.num_sentences = len(sentences)
        self.num_tokens = self._count_tokens(sentences)
        self.has_annotations = False
        self.has_translation = False
        self.has_char_vis = False
        self.translation = None

    def attach(self, annotations):
        """annotations are sentences from InputReader"""
        if not self._validate_annotations(annotations):
            raise ValueError("Annotations do not match input file")
        self._set_annotations(annotations)
        self.has_annotations = True

    def attach_translation(self, translation):
        self.has_translation = True
        self.translation = translation

    def attach_char_vis_data(self, data):
        self.has_char_vis = True
        self._set_char_vis_data(data)

    def _validate_annotations(self, annotations):
        if len(annotations) != self.num_sentences:
            return False
        # first word must match
        if annotations[0].columns[0].strings[0] != self.sentences[0].columns[0].strings[0]:
            return False
        return True

    def _set_annotations(self, annotations):
        for index, sentence in enumerate(self.sentences):
            # tag annotations stored in the second column
            sentence.attach(annotations[index].columns[1])

    def _set_char_vis_data(self, data):
        for index in range(len(self.sentences)):
            offset = 0
            char_weights = []
            tokens = self.sentences[index].columns[0].strings
            if index == 0:
                for token in tokens:
                    char_weights.append(['0' for x in range(len(token))])
                self.sentences[index].char_entity = char_weights
                continue

            weights = data[index - 1]
            for token in tokens:
                char_weights.append(list(weights[offset:offset+len(token)]))
                offset += len(token) + 1
            self.sentences[index].char_entity = char_weights

    @staticmethod
    def _count_tokens(sentences):
        total = 0
        for sentence in sentences:
            first_column = sentence.columns[0]
            total += len(first_column.strings)
        return total


class Sentence(object):
    """
    Represents a single sentence with its multiple columns of information (translations, PoS, gazetteer data, etc.)
    """
    def __init__(self, id):
        self.id = id
        self.columns = []
        self.char_entity = []

    @property
    def length(self):
        return len(self.columns[0].strings)

    def add(self, column):
        self.columns.append(column)

    def update(self, index, string):
        self.columns[index].strings.append(string)

    def attach(self, annotations):
        """attach annotations store in a SentenceColumn object to the tokens column"""
        self.columns[0].annotations = annotations.strings


class SentenceColumn(object):
    """
    Represents a sentence from a single column
    """
    def __init__(self, id, label):
        self.id = id
        self.label = label
        self.strings = []
        self.annotations = []

    @property
    def length(self):
        return len(self.strings)


class InputReader(object):
    """
    This parses a tsv file into a list of Sentence objects.
    Each Sentence has a list of SentenceColumn objects which correspond to the column data for that sentence.
    The first column in the csv must be the original tokens.
    If the first row is a header, the first column header must be TOKEN.
    There must be an empty line between sentences.
    """
    def __init__(self, filename):
        self.filename = filename
        self.num_columns = 0
        self.column_labels = []
        self.sentences = []
        self._load()

    def _load(self):
        with open(self.filename, 'r') as fp:
            reader = csv.reader(fp, delimiter='\t', quoting=csv.QUOTE_NONE)
            first_row = next(reader)
            if not first_row:
                # todo some sort of error message here
                return
            self.num_columns = len(first_row)
            has_header = self._is_header(first_row)
            self.column_labels = self._create_column_labels(first_row, has_header)

            data = [] if has_header else [first_row]
            for row in reader:
                if self._is_data(row):
                    data.append(row)
                elif data:
                    # sentence break
                    self.sentences.append(self._process_sentence(data))
                    data = []
            if data:
                # catch last sentence that might not have an empty line after it
                self.sentences.append(self._process_sentence(data))

    def _is_header(self, row):
        return row[0].lower() in ['tok', 'token', 'tokens']

    def _is_data(self, row):
        "Must have right number of columns and have data in one of the columns"
        if len(row) != self.num_columns:
            return False
        have_data = False
        for column in row:
            have_data |= bool(column)
        return have_data

    def _create_column_labels(self, row, use_values=True):
        if use_values:
            return [label.strip() for label in row]
        else:
            labels = []
            for index, value in enumerate(row, 1):
                labels.append('column {}'.format(index))
            return labels

    def _process_sentence(self, data):
        sentence = Sentence(len(self.sentences))
        for index, label in enumerate(self.column_labels):
            sentence.add(SentenceColumn(index, label))
        for row in data:
            for column, value in enumerate(row):
                sentence.update(column, value)
        return sentence


class OutputWriter(object):
    """
    Write the annotations
    """
    def __init__(self, directory):
        self.directory = directory

    def write(self, data):
        filename = os.path.join(self.directory, data['filename'] + '.anno')
        with open(filename, 'w') as fp:
            for token in data['tokens']:
                if token:
                    fp.write('{}\t{}\n'.format(token['token'], token['tag']))
                else:
                    fp.write('\n')
