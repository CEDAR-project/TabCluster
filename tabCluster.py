#!/usr/bin/env python

import argparse
import logging
import re
import numpy as np
import scipy.cluster.hierarchy
from Levenshtein import ratio
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import Namespace, RDF, SKOS
from SPARQLWrapper import SPARQLWrapper, JSON

class TabCluster:

    def __init__(self, __endpoint, __logLevel):
        self.log = logging.getLogger('TabCluster')
        self.log.setLevel(__logLevel)

        self.endpoint = __endpoint

        self.log.info('Reading remote SPARQL endpoint %s...' % self.endpoint)
        sparql = SPARQLWrapper(self.endpoint)
        sparql.setQuery("""
        PREFIX d2s: <http://www.data2semantics.org/core/>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

        SELECT DISTINCT ?dimlabel
        FROM <http://lod.cedar-project.nl/resource/BRT_1889_02_T1>
        WHERE {
        ?s d2s:dimension ?dimension .
        ?dimension skos:prefLabel ?dimlabel .
        }
        """)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()

        for result in results["results"]["bindings"]:
            self.log.debug(result["dimlabel"]["value"])

        ###

        fo = open('input', 'r')
        self.wordList = fo.readlines()

    def computeClusters(self):
        self.simMatrix = []
        # for i in range(len(self.wordList)):
        #     self.simMatrix.append([])
        #     for j in range(len(self.wordList)):
        #         self.simMatrix[i].append(self.distance((i,j)))

        print self.simMatrix       
        upperIndices = np.triu_indices(len(self.wordList), 1)
        upperTriangle = np.apply_along_axis(self.distance, 0, upperIndices)
        print scipy.cluster.hierarchy.linkage(upperTriangle)

    def distance(self, coord):
        i, j = coord
        return 1 - ratio(self.wordList[i], self.wordList[j])

    def URIzeString(self, __nonuri):
        return urllib.quote(re.sub('\s|\(|\)|,|\.','_',unicode(__nonuri).strip()).encode('utf-8', 'ignore'))
    
if __name__ == "__main__":
    # Parse commandline arguments
    parser = argparse.ArgumentParser(description="Extract SKOS taxonomies from Wikipedia pages")
    parser.add_argument('--endpoint', '-e',
                        help = "Target endpoint to cluster",
                        required = True)
    parser.add_argument('--verbose', '-v',
                        help = "Be verbose -- debug logging level",
                        required = False, 
                        action = 'store_true')
    parser.add_argument('--output', '-o',
                        help = "Output filename",
                        required = True)
    args = parser.parse_args()

    # Logging
    logLevel = logging.INFO
    if args.verbose:
        logLevel = logging.DEBUG

    logging.basicConfig(level=logLevel)

    logging.info('Initializing...')
    tabCluster = TabCluster(args.endpoint, logLevel)
    tabCluster.computeClusters()

    logging.info('Done.')
