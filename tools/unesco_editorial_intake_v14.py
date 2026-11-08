#!/usr/bin/env python3
"""Controle independant de decisions IA privees par rapport au tableau source.

Reception ne signifie jamais approbation, exactMatch, KS, ni KA.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
class IntakeError(ValueError):pass

def validate(bundle, tables, reviews=None):
    if bundle.get('format')!='kristal-manager.unesco-mt1-10-editorial-dispositions/1.0':
        raise IntakeError('Format de decision non reconnu')
    if any(bundle.get(k) is not False for k in ('admission_to_canon_authorized','publication_authorized','human_authorization_verified')):
        raise IntakeError('Demande d approbation ou publication illicite')
    if bundle.get('human_signed_approvals')!=0 or bundle.get('actual_KS_qualified')!=0 or bundle.get('canonical_KQ_KP_KA_KS_created')!=0:
        raise IntakeError('Approbation ou identifiant canonique invente')
    items=bundle.get('decisions',[])
    if not isinstance(items,list) or len(items)!=191:raise IntakeError('191 positions requises')
    ids=[(r.get('type'),r.get('ref')) for r in items]
    if len(set(ids))!=191:raise IntakeError('Position double')
    required={('IDENTITE',k) for k in tables['identities']}|{('PROPOSITION',k) for k in tables['proposals']}|{('SKOS_INTERNE',k) for k in tables['relations']}|{('SOURCE_CONCEPT10',k) for k,v in tables['sources'].items() if v['portee']=='CIBLE_CONCEPT10'}
    if set(ids)!=required:raise IntakeError('Ancrages des 191 positions invalides')
    kinds=Counter()
    for x in items:
        typ=x['type'];ref=x['ref'];kinds[typ]+=1
        if typ=='IDENTITE':
            src=tables['identities'][ref]
            if x['source_uri']!=src['unesco_uri'] or (x.get('qid_candidate') or '')!=src['qid_candidat']:
                raise IntakeError('Identite editee: '+ref)
        elif typ=='PROPOSITION':
            src=tables['proposals'][ref]
            if (x['unesco_id']!=src['unesco_id'] or x['original_en']!=src['statement_en'] or
                    x['original_sha256']!=sha256(src['statement_en'].encode('utf8')).hexdigest() or
                    x['evidence_status']!='NOT_ATTESTED'):
                raise IntakeError('Proposition sans ancrage: '+ref)
            if not x['chosen_text_en'].strip():raise IntakeError('Proposition vide')
            if reviews is not None:
                review=reviews['proposals'][ref]
                expected={'AVIS_DE_RECHERCHE_A_ETAYER':'RETENIR_COMME_HYPOTHESE_DANS_APERCU_PRIVE',
                    'REFORMULATION_SUGGEREE_A_REVOIR':'UTILISER_REFORMULATION_DANS_APERCU_PRIVE',
                    'PASSAGE_PRIMAIRE_A_CAPTURER_ET_ATTESTER':'RETENIR_SOUS_RESERVE_PREUVE_PRIMAIRE'}
                if (x['chosen_text_en']!=review['texte_propose_en'] or
                        x['decision_editoriale']!=expected.get(review['avis_chatgpt_non_signe'])):
                    raise IntakeError('Texte editorial ou statut modifie apres revue: '+ref)
        elif typ=='SKOS_INTERNE':
            src=tables['relations'][ref]
            if (x['source_unesco_id'],x['target_unesco_id'],x['relation_skos'],x['observations_reciproques'])!=(src['source_ou_membre_a'],src['cible_ou_membre_b'],src['relation_normalisee'],src['observations_reciproques']):
                raise IntakeError('Relation modifiee: '+ref)
            if reviews is not None:
                review=reviews['relations'][ref]
                expected='MAINTENIR_ET_SIGNALER_HIERARCHIE' if review['avis_chatgpt_non_signe']=='VERIFIER_HIERARCHIE_THEMATIQUE' else 'MAINTENIR_LIEN_SKOS_PRIVE'
                if x['decision_editoriale']!=expected:raise IntakeError('Avis relation modifie: '+ref)
        else:
            src=tables['sources'][ref]
            if x['url']!=src['url'] or x['KS_approved'] is not False:
                raise IntakeError('Fausse source KS: '+ref)
    return {'status':'KRISTALIZER_EDITORIAL_DECISIONS_VALID_PRIVATE_ONLY',
            'branch':'unesco-mt1-10','positions_verified':191,'split':dict(kinds),
            'human_signatures_verified':0,'canonical_KQ_KP_KA_KS_created':0,
            'canonical_admission_authorized':False,'publication_authorized':False}
