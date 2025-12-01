"""
Named Entity Recognition (NER) module for extracting entities from video transcripts.
Uses spaCy with downloadable models for local processing.
"""

import spacy
import re
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List, Tuple, Any

# Global variable to store loaded model
nlp_model = None

def load_ner_model():
    """Load spaCy NER model. Downloads if not available."""
    global nlp_model
    
    if nlp_model is not None:
        return nlp_model
    
    try:
        # Try to load the English model
        nlp_model = spacy.load("en_core_web_sm")
        print("Loaded spaCy model: en_core_web_sm")
    except OSError:
        print("Model 'en_core_web_sm' not found. Please download it using:")
        print("python -m spacy download en_core_web_sm")
        raise Exception("spaCy model not found. Run: python -m spacy download en_core_web_sm")
    
    return nlp_model

def extract_entities(transcript: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract named entities from transcript.
    Returns entities grouped by type.
    """
    nlp = load_ner_model()
    doc = nlp(transcript)
    
    entities = {
        'PERSON': [],
        'ORG': [],
        'GPE': [],  # Geopolitical entities (countries, cities, states)
        'LOC': [],  # Non-geopolitical locations
        'DATE': [],
        'TIME': [],
        'MONEY': [],
        'PERCENT': [],
        'EVENT': [],
        'PRODUCT': [],
        'LAW': [],
        'LANGUAGE': [],
        'NORP': []  # Nationalities or religious or political groups
    }
    
    seen_entities = set()
    
    for ent in doc.ents:
        entity_text = ent.text.strip()
        entity_key = f"{ent.label_}:{entity_text.lower()}"
        
        # Avoid duplicates
        if entity_key in seen_entities:
            continue
        seen_entities.add(entity_key)
        
        entity_info = {
            'text': entity_text,
            'label': ent.label_,
            'start': ent.start_char,
            'end': ent.end_char,
            'description': spacy.explain(ent.label_) or ent.label_
        }
        
        # Map spaCy labels to our categories
        if ent.label_ == 'PERSON':
            entities['PERSON'].append(entity_info)
        elif ent.label_ in ['ORG', 'ORGANIZATION']:
            entities['ORG'].append(entity_info)
        elif ent.label_ == 'GPE':
            entities['GPE'].append(entity_info)
        elif ent.label_ == 'LOC':
            entities['LOC'].append(entity_info)
        elif ent.label_ == 'DATE':
            entities['DATE'].append(entity_info)
        elif ent.label_ == 'TIME':
            entities['TIME'].append(entity_info)
        elif ent.label_ == 'MONEY':
            entities['MONEY'].append(entity_info)
        elif ent.label_ == 'PERCENT':
            entities['PERCENT'].append(entity_info)
        elif ent.label_ == 'EVENT':
            entities['EVENT'].append(entity_info)
        elif ent.label_ == 'PRODUCT':
            entities['PRODUCT'].append(entity_info)
        elif ent.label_ == 'LAW':
            entities['LAW'].append(entity_info)
        elif ent.label_ == 'LANGUAGE':
            entities['LANGUAGE'].append(entity_info)
        elif ent.label_ == 'NORP':
            entities['NORP'].append(entity_info)
    
    # Remove empty categories
    return {k: v for k, v in entities.items() if v}

def extract_timeline(transcript: str) -> List[Dict[str, Any]]:
    """
    Extract timeline of events and dates from transcript.
    """
    nlp = load_ner_model()
    doc = nlp(transcript)
    
    timeline = []
    seen_dates = set()
    
    # Extract dates and their context
    for ent in doc.ents:
        if ent.label_ == 'DATE':
            date_text = ent.text.strip()
            if date_text.lower() in seen_dates:
                continue
            seen_dates.add(date_text.lower())
            
            # Get surrounding context (sentence)
            sentence = ent.sent.text.strip()
            
            timeline_item = {
                'date': date_text,
                'context': sentence,
                'position': ent.start_char
            }
            timeline.append(timeline_item)
    
    # Sort by position in transcript
    timeline.sort(key=lambda x: x['position'])
    
    return timeline

def extract_key_facts(transcript: str, entities: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Extract key facts from transcript using entities and patterns.
    """
    nlp = load_ner_model()
    doc = nlp(transcript)
    
    facts = {
        'people_mentioned': len(entities.get('PERSON', [])),
        'organizations': len(entities.get('ORG', [])),
        'locations': len(entities.get('GPE', [])) + len(entities.get('LOC', [])),
        'dates_mentioned': len(entities.get('DATE', [])),
        'top_people': [],
        'top_organizations': [],
        'top_locations': []
    }
    
    # Get most mentioned people
    person_counts = Counter([e['text'] for e in entities.get('PERSON', [])])
    facts['top_people'] = [{'name': name, 'mentions': count} 
                          for name, count in person_counts.most_common(5)]
    
    # Get most mentioned organizations
    org_counts = Counter([e['text'] for e in entities.get('ORG', [])])
    facts['top_organizations'] = [{'name': name, 'mentions': count} 
                                 for name, count in org_counts.most_common(5)]
    
    # Get most mentioned locations
    location_counts = Counter([e['text'] for e in entities.get('GPE', []) + entities.get('LOC', [])])
    facts['top_locations'] = [{'name': name, 'mentions': count} 
                             for name, count in location_counts.most_common(5)]
    
    # Extract numbers and statistics
    numbers = re.findall(r'\b\d+(?:,\d{3})*(?:\.\d+)?\b', transcript)
    facts['numbers_mentioned'] = len(numbers)
    
    # Extract questions (sentences ending with ?)
    questions = [s.strip() for s in transcript.split('.') if '?' in s]
    facts['questions_asked'] = len(questions)
    
    return facts

def extract_relationships(transcript: str, entities: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Extract relationships between entities (basic co-occurrence analysis).
    """
    nlp = load_ner_model()
    doc = nlp(transcript)
    
    relationships = []
    people = [e['text'] for e in entities.get('PERSON', [])]
    orgs = [e['text'] for e in entities.get('ORG', [])]
    locations = [e['text'] for e in entities.get('GPE', []) + entities.get('LOC', [])]
    
    # Find co-occurrences in sentences
    for sent in doc.sents:
        sent_text = sent.text
        sent_people = [p for p in people if p in sent_text]
        sent_orgs = [o for o in orgs if o in sent_text]
        sent_locations = [l for l in locations if l in sent_text]
        
        # Person-Organization relationships
        for person in sent_people:
            for org in sent_orgs:
                relationships.append({
                    'type': 'PERSON-ORG',
                    'entity1': person,
                    'entity2': org,
                    'context': sent_text[:200]  # First 200 chars of sentence
                })
        
        # Person-Location relationships
        for person in sent_people:
            for loc in sent_locations:
                relationships.append({
                    'type': 'PERSON-LOC',
                    'entity1': person,
                    'entity2': loc,
                    'context': sent_text[:200]
                })
        
        # Organization-Location relationships
        for org in sent_orgs:
            for loc in sent_locations:
                relationships.append({
                    'type': 'ORG-LOC',
                    'entity1': org,
                    'entity2': loc,
                    'context': sent_text[:200]
                })
    
    # Remove duplicates
    seen = set()
    unique_relationships = []
    for rel in relationships:
        key = (rel['type'], rel['entity1'], rel['entity2'])
        if key not in seen:
            seen.add(key)
            unique_relationships.append(rel)
    
    return unique_relationships[:20]  # Limit to top 20

def process_transcript(transcript: str) -> Dict[str, Any]:
    """
    Main function to process transcript and extract all NER information.
    """
    try:
        entities = extract_entities(transcript)
        timeline = extract_timeline(transcript)
        facts = extract_key_facts(transcript, entities)
        relationships = extract_relationships(transcript, entities)
        
        return {
            'entities': entities,
            'timeline': timeline,
            'key_facts': facts,
            'relationships': relationships,
            'success': True
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

