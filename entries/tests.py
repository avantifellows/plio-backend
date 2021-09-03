import json
from django.urls import reverse
from rest_framework import status

from plio.tests import BaseTestCase
from plio.models import Plio, Video, Item
from entries.models import Session


class SessionTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        # seed a video
        self.video = Video.objects.create(
            title="Video 1",
            url="https://www.youtube.com/watch?v=vnISjBbrMUM",
            duration=10,
        )
        # seed a plio
        self.plio = Plio.objects.create(
            name="Plio", video=self.video, created_by=self.user
        )

    def test_cannot_create_session_for_draft_plio(self):
        response = self.client.post(reverse("sessions-list"), {"plio": self.plio.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            json.loads(response.content)["non_field_errors"][0],
            "A session can only be created for a published plio",
        )

    def test_can_create_session_for_published_plio(self):
        # set plio as published
        self.plio.status = "published"
        self.plio.save()
        response = self.client.post(reverse("sessions-list"), {"plio": self.plio.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_fresh_session_created_if_no_old_sessions_exist(self):
        """
        If no old sessions exist, a fresh session should be
        created and should contain all default values
        """
        # seed two items linked to plio
        item_1 = Item.objects.create(type="question", plio=self.plio, time=1)
        item_2 = Item.objects.create(type="question", plio=self.plio, time=2)

        # publish plio
        self.plio.status = "published"
        self.plio.save()

        # create a new session for `plio` by `user`
        response = self.client.post(reverse("sessions-list"), {"plio": self.plio.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["is_first"])
        self.assertEqual(len(response.data["session_answers"]), 2)
        self.assertEqual(response.data["session_answers"][0]["item_id"], item_1.id)
        self.assertEqual(response.data["session_answers"][1]["item_id"], item_2.id)
        self.assertEqual(response.data["retention"], ("0," * self.video.duration)[:-1])

    def test_old_session_can_be_updated(self):
        """
        An already created session can be updated with details
        """
        # publish plio
        self.plio.status = "published"
        self.plio.save()

        # create a new, first session for plio
        response = self.client.post(reverse("sessions-list"), {"plio": self.plio.id})
        session_1 = response.data
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(session_1["is_first"])

        # update that session with some details
        response = self.client.put(
            reverse("sessions-detail", args=[session_1["id"]]),
            {
                "plio": self.plio.id,
                "watch_time": 5.00,
                "retention": "1,1,1,1,1,0,0,0,0,0",
            },
        )
        session_1_updated = response.data
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(session_1_updated["is_first"])
        self.assertEqual(session_1_updated["id"], session_1["id"])

    def test_old_session_details_used_if_old_sessions_exist(self):
        """
        If old sessions exist, a new session created should carry
        over all the details from the older session
        """
        # seed two items linked to plio
        Item.objects.create(type="question", plio=self.plio, time=1)
        Item.objects.create(type="question", plio=self.plio, time=2)

        # publish plio
        self.plio.status = "published"
        self.plio.save()

        # create a new, first session for plio
        response = self.client.post(reverse("sessions-list"), {"plio": self.plio.id})
        session_1 = response.data
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(session_1["is_first"])

        # update that session with some details
        response = self.client.put(
            reverse("sessions-detail", args=[session_1["id"]]),
            {
                "plio": self.plio.id,
                "watch_time": 5.00,
                "retention": "1,1,1,1,1,0,0,0,0,0",
            },
        )
        session_1_updated = response.data
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(session_1_updated["is_first"])
        self.assertEqual(session_1_updated["id"], session_1["id"])

        # creating a new session for this user-plio combination
        # details of the last sessions should be passed along to this session
        response = self.client.post(reverse("sessions-list"), {"plio": self.plio.id})
        session_2 = response.data
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(session_2["id"], session_1_updated["id"])
        self.assertEqual(len(session_2["session_answers"]), 2)
        self.assertEqual(session_2["retention"], session_1_updated["retention"])
        self.assertEqual(session_2["watch_time"], session_1_updated["watch_time"])
        self.assertFalse(session_2["is_first"])

        # mocking the answering of a question
        response = self.client.put(
            reverse(
                "session-answers-detail", args=[session_2["session_answers"][0]["id"]]
            ),
            {
                "id": session_2["session_answers"][0]["id"],
                "item": session_2["session_answers"][0]["item_id"],
                "session": session_2["id"],
                "answer": 0,
            },
        )

        # create a new session for the user-plio combination,
        # it should have the session_answer details of session_2
        response = self.client.post(reverse("sessions-list"), {"plio": self.plio.id})
        session_3 = response.data
        #
        session_2_instance = Session.objects.filter(id=int(session_2["id"])).first()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            session_3["session_answers"][0]["item_id"],
            session_2_instance.sessionanswer_set.values()[0]["item_id"],
        )
        self.assertEqual(
            session_3["session_answers"][0]["answer"],
            session_2_instance.sessionanswer_set.values()[0]["answer"],
        )

    def test_deleting_plio_deletes_sessions(self):
        """Deleting a plio should delete the sessions associated with it"""
        # create session for plio
        self.plio.status = "published"
        self.plio.save()
        response = self.client.post(reverse("sessions-list"), {"plio": self.plio.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        session_id = response.data["id"]

        # delete the plio associated with the question
        response = self.client.delete(f"/api/v1/plios/{self.plio.uuid}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # fetching the session created above should give an error
        response = self.client.get(f"/api/v1/sessions/{session_id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SessionAnswerTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

    def test_for_session_answer(self):
        # write API calls here
        self.assertTrue(True)


class EventTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

    def test_for_event(self):
        # write API calls here
        self.assertTrue(True)
