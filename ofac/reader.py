#!/usr/bin/env python3

from timeit import default_timer as timer
from dataobjects import NamePart
from dataobjects import NameAlias
from datetime import datetime
import sdn as parser


def extract_dates(DatePeriod):
    start_date_from = create_single_date(DatePeriod.Start.From)
    start_date_to = create_single_date(DatePeriod.Start.To)

    end_date_from = create_single_date(DatePeriod.End.From)
    end_date_to = create_single_date(DatePeriod.End.To)

    if start_date_from == start_date_to:
        if end_date_from == end_date_to:
            if start_date_from == end_date_from:
                return start_date_from  # all values equal, this is a single exact date
            else:
                # TODO ranges not supported
                return None  # (start_date_from, end_date_from) # equal pairs
    else:
        # TODO ranges not supported
        # what is this case supposed to represent? that the whole year is included?
        # values = [start_date_from, start_date_to, end_date_to, end_date_from]
        # return tuple(values)
        return None


def create_single_date(date):
    month = date.Month.valueOf_
    day = date.Day.valueOf_
    if len(month) == 1:
        month = "0" + month
    if len(day) == 1:
        day = "0" + day

    return datetime.strptime("{} {} {}".format(date.Year.valueOf_, month, day), '%Y %m %d')




def load_sdn_sanctions(sdn_filename='sdn_advanced_2024.xml'):
    sdn_list = parser.parse(sdn_filename, silence=True)
    return load_sanctions(sdn_list)


def load_consolidated_sanctions(cons_filename='cons_advanced.xml'):
    consolidated_list = parser.parse(cons_filename, silence=True)
    return load_sanctions(consolidated_list)


def load_sanctions(sanction_list):
    id_to_name_entities = {}
    id_to_name_persons = {}
    entity_name_to_id_map = {}

    sanctioned_parties = sanction_list.DistinctParties.get_DistinctParty()

    for party in sanctioned_parties:
        name_aliases = []
        date_aliases = []
        for profile in party.Profile:
            for feature in profile.Feature:
                if feature.FeatureTypeID == 8:  # birthdate
                    for version in feature.FeatureVersion:
                        # there is currently never more than one version in the list, and its unclear how versions are to be marked current and outdated
                        if version.ReliabilityID == 1561:  # 1561 means it's been proven false, so skip it
                            continue

                        for period in version.DatePeriod:
                            date_aliases.append(period)
            for identity in profile.Identity:
                for alias in identity.Alias:
                    if alias.LowQuality == False:  # TODO include the low quality aliases as well, but mark then accordingly
                        for name in alias.DocumentedName:
                            parts = []
                            for namepart in name.DocumentedNamePart:
                                namepart_value = namepart.NamePartValue
                                if namepart_value.ScriptID == 215:  # our input is latin only, so we match against latin only
                                    namevalue = namepart_value.valueOf_
                                    parts.append(namevalue)
                            if parts:
                                name_parts = [NamePart(p) for p in parts]
                                name_aliases.append((NameAlias(name_parts)))

        if name_aliases:
            if profile.PartySubTypeID == 4:  # person
                dates = [extract_dates(d) for d in date_aliases if d]

                id_to_name_persons[party.FixedRef] = (name_aliases, dates)
            else:  # not a person, type 3 is a company
                id_to_name_entities[party.FixedRef] = (name_aliases, [])
                for name in name_aliases:
                    entity_name_to_id_map[str(name)] = party.FixedRef

    return (id_to_name_persons, id_to_name_entities, entity_name_to_id_map)


def printSubjects(bin_to_id):
    for reference, names in bin_to_id.items():
        print(reference, names)

import csv
import io
import sys

def import_test_entities(filename):
    # reads a semi-colon value separated file, one entity per list
    # format is id;name
    with io.open(filename, 'r', newline='', encoding='utf-8') as csvfile:
        cvs_reader = csv.DictReader(csvfile, delimiter=';')
        try:
            subjects = []
            rows = list(cvs_reader)  # read it all into memory
            for row in rows:
                value = (row['id'], row['name'])
                subjects.append(value)
            return subjects
        except csv.Error as e:
            sys.exit('file {}, line {}: {}'.format(filename, cvs_reader.line_num, e))

def execute_test_queries(name_to_id_map, filename="internal_test_queries.csv"):
    test_subjects = import_test_entities(filename)
    test_subject_count = len(test_subjects)
    total_matches = 0
    total_records = 0
    matches = []
    print("Searching for {} test-subjects read from file '{}'".format(test_subject_count, filename))
    for (id, name) in test_subjects:
        if name in name_to_id_map.keys():
            matches.append((id, name, name_to_id_map[name]))

    for match in matches:
        print("{} {} {} \n".format(match[0], match[1], match[2]))
    print("\nFound in total {} matches, searched for {} customers.".format(len(matches), test_subject_count))

if __name__ == "__main__":
    (id_to_name_persons_sdn, id_to_name_entities_sdn, entity_name_to_id_map) = load_sdn_sanctions()

    print("Loaded {} entities and {} persons".format(len(id_to_name_entities_sdn),
                                                     len(id_to_name_persons_sdn)))

    #printSubjects(entity_name_to_id_map)
    #print(len(id_to_name_entities_sdn))
    #print(len(entity_name_to_id_map))
    # printSubjects(id_to_name_persons_sdn)
    #print(len(id_to_name_persons_sdn))

    execute_test_queries(entity_name_to_id_map, "sentry_entity_name_list.csv")
