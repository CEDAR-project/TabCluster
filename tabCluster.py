#!/usr/bin/env python

import argparse
import logging
import re
import numpy as np
import scipy.cluster.hierarchy
import codecs
from time import sleep
from Levenshtein import ratio
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import Namespace, RDF, SKOS
from SPARQLWrapper import SPARQLWrapper, JSON

class TabCluster:
    stopWords = ['en', 'de', 'der', 'van', '\'', '\"']

    def __init__(self, __endpoint, __logLevel):
        self.log = logging.getLogger('TabCluster')
        self.log.setLevel(__logLevel)

        self.endpoint = __endpoint

        # Local data structures
        self.tree = {} # Stores the clusters
        self.clusterDistance = {} # Distances between clusters
        self.clustersToLabel = [] # Clusters to label acc SciPy criteria
        self.clusterTags = {} # Tags given to each cluster to label

        # Data load
        fo = codecs.open('input', encoding='utf-8')
        self.wordList = list(set(fo.read().splitlines()))
        self.log.debug('Word list contains %s items' % len(self.wordList))

        self.clusterIndex = len(self.wordList)
        self.computeClusters()
        self.root = self.clusterIndex - 1

        self.clustersUnderThreshold(self.root, self.clustersToLabel,  0.7*max(self.clusterDistance.values()))


    def computeClusters(self):
        upperIndices = np.triu_indices(len(self.wordList), 1)
        upperTriangle = np.apply_along_axis(self.levenshteinDistance, 0, upperIndices)
        self.cluster = scipy.cluster.hierarchy.linkage(upperTriangle)
        self.log.debug(self.cluster)

        for i in self.cluster:
            indexA = int(i[0])
            indexB = int(i[1])
            elemA = self.wordList[indexA] if indexA < len(self.wordList) else indexA
            elemB = self.wordList[indexB] if indexB < len(self.wordList) else indexB
            self.tree[self.clusterIndex] = []
            self.tree[self.clusterIndex].append(elemA)
            self.tree[self.clusterIndex].append(elemB)
            self.clusterDistance[self.clusterIndex] = i[2]
            self.clusterIndex += 1

    def getTreeElems(self, node, bag):
        if not isinstance(node, int):
            bag.append(node)
        else:
            self.getTreeElems(self.tree[node][0], bag)
            self.getTreeElems(self.tree[node][1], bag)

    def clustersUnderThreshold(self, node, bag, t):
        if node not in self.tree:
            return None
        if self.clusterDistance[node] < t:
            return bag.append(node)
        else:
            self.clustersUnderThreshold(self.tree[node][0], bag, t)
            self.clustersUnderThreshold(self.tree[node][1], bag, t)

    def tagsByPopularTerm(self):
        clusterRepresentative = {}
        for b in self.clustersToLabel:
            bag = []
            self.getTreeElems(b, bag)
            print bag
            bagSize = len(bag)
            bagDict = {}
            for elem in bag:
                terms = re.split('\s|\-', elem.lower().replace(":", "").replace("\"", "").replace("\'", ""))
                for t in terms:
                    if t not in bagDict:
                        bagDict[t] = 1
                    else:
                        bagDict[t] += 1
            if 'de' in bagDict:
                    del bagDict['de']
            if 'en' in bagDict:
                del bagDict['en']
            if 'der' in bagDict:
                del bagDict['der']
            if 'van' in bagDict:
                del bagDict['van']
            if '' in bagDict:
                del bagDict['']
            print bagDict
            bagRepresentative = max(bagDict.iterkeys(), key=(lambda key: bagDict[key]))
            print "BAGWINNER: %s" % bagRepresentative
            clusterRepresentative[b] = bagRepresentative

        print clusterRepresentative

        for bagRepresentative in clusterRepresentative.values():
            sparql = SPARQLWrapper('http://nl.dbpedia.org/sparql')
            print "Processing %s..." % bagRepresentative
            query = u"""
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
            PREFIX dcterms: <http://purl.org/dc/terms/>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
            SELECT DISTINCT ?concept ?subject 
            WHERE {
            ?concept dcterms:subject ?subject .
            ?concept rdfs:label ?label . 
            ?label bif:contains \"\'%s\'\"@nl 
            OPTION (score ?sc) .
            } ORDER BY ASC(STRLEN(?concept))
            LIMIT 10""" % bagRepresentative
            # print query
            sparql.setQuery(query)
            sparql.setReturnFormat(JSON)
            results = sparql.query().convert()
            sleep(1)
            for result in results["results"]["bindings"]:
                print result["concept"]["value"], result["subject"]["value"]

    def tagsByPopularCategory(self):
        clusterSupers = {}
        for b in self.clustersToLabel:
            bag = []
            self.getTreeElems(b, bag)
            print bag
            bagSupers = {}
            for elem in bag:
                clean = self.removeStopWords(elem)
                # print clean
                sparql = SPARQLWrapper('http://nl.dbpedia.org/sparql')
                # print "Processing %s..." % clean
                query = u"""
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
                PREFIX dcterms: <http://purl.org/dc/terms/>
                PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
                SELECT DISTINCT ?concept
                WHERE {
                ?concept rdfs:label ?label . 
                ?label bif:contains \"\'%s\'\"@nl 
                OPTION (score ?sc) .
                } ORDER BY DESC(?sc)
                LIMIT 25""" % "\' or \'".join(clean.split(' '))
                # print query
                sparql.setQuery(query)
                sparql.setReturnFormat(JSON)
                results = sparql.query().convert()
                sleep(1)
                for result in results["results"]["bindings"]:
                    uri = result["concept"]["value"]
                    # print uri
                    if uri not in bagSupers:
                        bagSupers[uri] = 1
                    else:
                        bagSupers[uri] += 1
                # print sorted(bagSupers.iteritems(), key=operator.itemgetter(1))
            clusterRepresentative = max(bagSupers.iterkeys(), key=(lambda key: bagSupers[key]))
            print clusterRepresentative

    def layoutClusters(self):
        dendogram = scipy.cluster.hierarchy.dendrogram(self.cluster)

    def levenshteinDistance(self, coord):
        i, j = coord
        return 1 - ratio(self.wordList[i], self.wordList[j])

    def removeStopWords(self, s):
        wordlist = re.split('\s|\-|\'|\"|\:', s)
        for w in self.stopWords:
            if w in wordlist:
                wordlist.remove(w)        
        return re.sub('(^|\s)\S*\.', '', re.sub('\s+', ' ', u" ".join(wordlist))).strip()

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
    print tabCluster.clustersToLabel
    tabCluster.tagsByPopularTerm()
    tabCluster.tagsByPopularCategory()

    logging.info('Done.')
