"""
Unit tests for Candidate Management (Requirements #2).
Tests adding candidate, viewing list, searching by name/phone/email/code, and viewing details.
"""

from django.test import TestCase
from apps.candidates.application.services import CandidateService
from apps.candidates.infrastructure.repositories import DjangoCandidateRepository
from apps.candidates.infrastructure.models import Candidate, MessageStatus


class CandidateManagementTests(TestCase):
    def setUp(self):
        self.repository = DjangoCandidateRepository()
        self.service = CandidateService(repository=self.repository)

    def test_add_and_retrieve_candidate(self):
        candidate = self.service.create_candidate(
            full_name="Neha Patel",
            mobile_number="+919876543222",
            email="neha.patel@example.com",
        )
        self.assertIsNotNone(candidate.id)
        self.assertEqual(candidate.full_name, "Neha Patel")
        self.assertEqual(candidate.email, "neha.patel@example.com")
        self.assertEqual(candidate.status, MessageStatus.NA)

        fetched = self.service.get_candidate(candidate.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.candidate_id, candidate.candidate_id)

    def test_search_candidates(self):
        self.service.create_candidate("Rahul Sharma", "+919876543201", "rahul@test.com")
        self.service.create_candidate("Priya Shah", "+919876543202", "priya@test.com")
        self.service.create_candidate("Rohan Mehta", "+919876543203", "rohan@other.com")

        # Search by name
        results, count = self.service.list_candidates(search="Priya")
        self.assertEqual(count, 1)
        self.assertEqual(results[0].full_name, "Priya Shah")

        # Search by phone
        results, count = self.service.list_candidates(search="543203")
        self.assertEqual(count, 1)
        self.assertEqual(results[0].full_name, "Rohan Mehta")

        # Search by email
        results, count = self.service.list_candidates(search="test.com")
        self.assertEqual(count, 2)
