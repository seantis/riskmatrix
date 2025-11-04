import unittest
from pyramid import testing
from pyramid.i18n import get_localizer
from pyramid.i18n import TranslationStringFactory

_ = TranslationStringFactory('riskmatrix')

class TestTranslations(unittest.TestCase):
    def setUp(self):
        self.config = testing.setUp()
        
    def tearDown(self):
        testing.tearDown()
        
    def test_german_translations(self):
        """Test German translations for key components."""
        request = testing.DummyRequest()
        request.locale_name = 'de'
        localizer = get_localizer(request)
        
        # Risk Assessment related translations
        self.assertEqual(localizer.translate(_('Identify Risks')), 'Risiken identifizieren')
        self.assertEqual(localizer.translate(_('Assess Impact')), 'Auswirkung bewerten')
        self.assertEqual(localizer.translate(_('Assess Likelihood')), 'Wahrscheinlichkeit bewerten')
        self.assertEqual(localizer.translate(_('Generate Risk Matrix')), 'Risikomatrix erstellen')
        self.assertEqual(localizer.translate(_('Plan Actions')), 'Maßnahmen planen')
        
        # Risk Catalog related translations
        self.assertEqual(localizer.translate(_('Risk Catalog')), 'Risikokatalog')
        self.assertEqual(localizer.translate(_('Add Risk Catalog')), 'Risikokatalog hinzufügen')
        self.assertEqual(localizer.translate(_('Delete Risk Catalog')), 'Risikokatalog löschen')
        self.assertEqual(localizer.translate(_('Edit Catalog')), 'Katalog bearbeiten')
        
        # Asset related translations
        self.assertEqual(localizer.translate(_('Assets')), 'Assets')
        self.assertEqual(localizer.translate(_('Add Asset')), 'Asset hinzufügen')
        self.assertEqual(localizer.translate(_('Delete Asset')), 'Asset löschen')
        
        # Risk Matrix comparison translations
        self.assertEqual(localizer.translate(_('Change in Likelihood')), 'Änderung der Wahrscheinlichkeit')
        self.assertEqual(localizer.translate(_('Change in Impact')), 'Änderung der Auswirkung')
        self.assertEqual(localizer.translate(_('Overview of all Risk Assessments')), 'Übersicht aller Risikobewertungen')
        
        # AI Risk Catalog Generation translations
        self.assertEqual(
            localizer.translate(_('What is the main business area of the company?')),
            'In welchem Geschäftsbereich ist das Unternehmen tätig?'
        )
        self.assertEqual(
            localizer.translate(_('Please describe your main customer portfolio in one sentence')),
            'Bitte beschreiben Sie Ihr Hauptkundenportfolio in einem Satz'
        )
        self.assertEqual(
            localizer.translate(_('What IT services are operated by external partners?')),
            'Welche IT-Dienstleistungen werden von externen Partnern betrieben?'
        )
        
    def test_french_translations(self):
        """Test French translations for key components."""
        request = testing.DummyRequest()
        request.locale_name = 'fr'
        localizer = get_localizer(request)
        
        # Risk Assessment related translations
        self.assertEqual(localizer.translate(_('Identify Risks')), 'Identifier les risques')
        self.assertEqual(localizer.translate(_('Assess Impact')), "Évaluer l'impact")
        self.assertEqual(localizer.translate(_('Assess Likelihood')), 'Évaluer la probabilité')
        self.assertEqual(localizer.translate(_('Generate Risk Matrix')), 'Générer la matrice de risques')
        self.assertEqual(localizer.translate(_('Plan Actions')), 'Planifier les actions')
        
        # Risk Catalog related translations
        self.assertEqual(localizer.translate(_('Risk Catalog')), 'Catalogue des risques')
        self.assertEqual(localizer.translate(_('Add Risk Catalog')), 'Ajouter un catalogue de risques')
        self.assertEqual(localizer.translate(_('Delete Risk Catalog')), 'Supprimer le catalogue des risques')
        self.assertEqual(localizer.translate(_('Edit Catalog')), 'Modifier le catalogue')
        
        # Asset related translations
        self.assertEqual(localizer.translate(_('Assets')), 'Actifs')
        self.assertEqual(localizer.translate(_('Add Asset')), 'Ajouter un actif')
        self.assertEqual(localizer.translate(_('Delete Asset')), "Supprimer l'actif")
        
        # Risk Matrix comparison translations
        self.assertEqual(localizer.translate(_('Change in Likelihood')), 'Changement de probabilité')
        self.assertEqual(localizer.translate(_('Change in Impact')), "Changement d'impact")
        self.assertEqual(
            localizer.translate(_('Overview of all Risk Assessments')), 
            'Aperçu de toutes les évaluations des risques'
        )
        
        # AI Risk Catalog Generation translations
        self.assertEqual(
            localizer.translate(_('What is the main business area of the company?')),
            "Quel est le principal domaine d'activité de l'entreprise ?"
        )
        self.assertEqual(
            localizer.translate(_('Please describe your main customer portfolio in one sentence')),
            'Veuillez décrire votre portefeuille client principal en une phrase'
        )
        self.assertEqual(
            localizer.translate(_('What IT services are operated by external partners?')),
            'Quels services informatiques sont gérés par des partenaires externes ?'
        ) 