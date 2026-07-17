import factory

from entries.models import Event, Session, SessionAnswer
from experiments.models import Experiment
from organizations.models import Organization
from plio.models import Image, Item, Plio, Question, Video
from users.models import User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: "user{}@example.com".format(n))
    mobile = factory.Sequence(lambda n: "+910000{:06d}".format(n))


class OrganizationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Organization

    name = factory.Sequence(lambda n: "Organization {}".format(n))
    shortcode = factory.Sequence(lambda n: "org-{}".format(n))
    schema_name = factory.Sequence(lambda n: "org_{}".format(n))


class ImageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Image

    url = factory.django.ImageField(filename="question.png")


class VideoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Video

    url = "https://www.youtube.com/watch?v=vnISjBbrMUM"
    title = "Factory video"
    duration = 60


class PlioFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Plio

    video = factory.SubFactory(VideoFactory)
    name = factory.Sequence(lambda n: "Plio {}".format(n))
    created_by = factory.SubFactory(UserFactory)
    status = "draft"

    class Params:
        published = factory.Trait(status="published")


class ItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Item

    plio = factory.SubFactory(PlioFactory)
    time = 10


class QuestionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Question

    item = factory.SubFactory(ItemFactory)
    text = "Factory question"
    type = "mcq"
    options = ["A", "B"]
    correct_answer = 0

    class Params:
        mcq = factory.Trait(type="mcq", options=["A", "B"], correct_answer=0)
        checkbox = factory.Trait(
            type="checkbox", options=["A", "B"], correct_answer=[0]
        )
        subjective = factory.Trait(type="subjective", options=None, correct_answer=None)


class ExperimentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Experiment

    name = factory.Sequence(lambda n: "Experiment {}".format(n))
    description = "Factory experiment"
    created_by = factory.SubFactory(UserFactory)


class SessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Session

    user = factory.SubFactory(UserFactory)
    plio = factory.SubFactory(PlioFactory)


class SessionAnswerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SessionAnswer

    session = factory.SubFactory(SessionFactory)
    item = factory.LazyAttribute(lambda answer: ItemFactory(plio=answer.session.plio))
    answer = 0


class EventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Event

    session = factory.SubFactory(SessionFactory)
    type = "played"
    player_time = 0
    details = factory.LazyFunction(dict)
