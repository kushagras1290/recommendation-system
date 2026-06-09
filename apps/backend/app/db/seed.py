from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone

import structlog

from app.db.database import get_db
from app.db.models import Experiment, Interaction, Item, User

logger = structlog.get_logger(__name__)

MOVIES: list[dict] = [
    {"title": "The Shawshank Redemption", "category": "Drama", "year": 1994, "rating": 9.3, "description": "Two imprisoned men bond over years finding solace and redemption."},
    {"title": "The Godfather", "category": "Crime", "year": 1972, "rating": 9.2, "description": "The aging patriarch of an organized crime dynasty transfers control to his son."},
    {"title": "The Dark Knight", "category": "Action", "year": 2008, "rating": 9.0, "description": "Batman faces the Joker, a criminal mastermind who plunges Gotham into chaos."},
    {"title": "12 Angry Men", "category": "Drama", "year": 1957, "rating": 9.0, "description": "A jury holdout attempts to prevent a miscarriage of justice."},
    {"title": "Schindler's List", "category": "Drama", "year": 1993, "rating": 9.0, "description": "Oskar Schindler saves Jewish refugees during the Holocaust."},
    {"title": "The Lord of the Rings: The Return of the King", "category": "Fantasy", "year": 2003, "rating": 9.0, "description": "Gandalf and Aragorn lead the World of Men against Sauron's army."},
    {"title": "Pulp Fiction", "category": "Crime", "year": 1994, "rating": 8.9, "description": "Lives of two mob hitmen, a boxer, and a gangster intertwine."},
    {"title": "The Lord of the Rings: The Fellowship of the Ring", "category": "Fantasy", "year": 2001, "rating": 8.8, "description": "A meek hobbit sets out on a journey to destroy an ancient ring."},
    {"title": "The Good, the Bad and the Ugly", "category": "Western", "year": 1966, "rating": 8.8, "description": "Three gunslingers compete to find a fortune in buried Confederate gold."},
    {"title": "Forrest Gump", "category": "Drama", "year": 1994, "rating": 8.8, "description": "The presidencies of Kennedy through Bush through the eyes of an Alabama man."},
    {"title": "Inception", "category": "Sci-Fi", "year": 2010, "rating": 8.8, "description": "A thief plants an idea into a target's mind during their dreams."},
    {"title": "Fight Club", "category": "Drama", "year": 1999, "rating": 8.8, "description": "An insomniac office worker and a soap salesman form an underground fight club."},
    {"title": "The Matrix", "category": "Sci-Fi", "year": 1999, "rating": 8.7, "description": "A hacker discovers reality is a simulation and joins a rebellion."},
    {"title": "Goodfellas", "category": "Crime", "year": 1990, "rating": 8.7, "description": "The story of Henry Hill and his life in the mob."},
    {"title": "Star Wars: A New Hope", "category": "Sci-Fi", "year": 1977, "rating": 8.6, "description": "A farm boy discovers he has the power to save the galaxy."},
    {"title": "One Flew Over the Cuckoo's Nest", "category": "Drama", "year": 1975, "rating": 8.7, "description": "A criminal pleads insanity, entering a mental institution."},
    {"title": "Interstellar", "category": "Sci-Fi", "year": 2014, "rating": 8.7, "description": "Astronauts travel through a wormhole near Saturn in search of a new home."},
    {"title": "Parasite", "category": "Thriller", "year": 2019, "rating": 8.5, "description": "A poor family schemes to become employed by a wealthy family."},
    {"title": "The Silence of the Lambs", "category": "Thriller", "year": 1991, "rating": 8.6, "description": "An FBI trainee enlists Dr. Hannibal Lecter to catch a serial killer."},
    {"title": "Saving Private Ryan", "category": "War", "year": 1998, "rating": 8.6, "description": "WWII soldiers go on a mission to save a paratrooper."},
    {"title": "Spirited Away", "category": "Animation", "year": 2001, "rating": 8.6, "description": "A girl gets trapped in a mysterious world of spirits."},
    {"title": "The Green Mile", "category": "Fantasy", "year": 1999, "rating": 8.6, "description": "Death row guards experience supernatural events with a new inmate."},
    {"title": "Whiplash", "category": "Drama", "year": 2014, "rating": 8.5, "description": "A jazz drummer battles to make it in a music conservatory."},
    {"title": "The Prestige", "category": "Thriller", "year": 2006, "rating": 8.5, "description": "Two rival magicians go to extremes to outdo each other."},
    {"title": "The Departed", "category": "Crime", "year": 2006, "rating": 8.5, "description": "An undercover cop infiltrates the Irish mob."},
    {"title": "Avengers: Endgame", "category": "Action", "year": 2019, "rating": 8.4, "description": "The Avengers assemble once more to reverse Thanos's devastating actions."},
    {"title": "Gladiator", "category": "Action", "year": 2000, "rating": 8.5, "description": "A Roman general seeks revenge against a corrupt emperor."},
    {"title": "The Lion King", "category": "Animation", "year": 1994, "rating": 8.5, "description": "A young lion prince flees his kingdom only to learn the true meaning of responsibility."},
    {"title": "Back to the Future", "category": "Sci-Fi", "year": 1985, "rating": 8.5, "description": "A teenager is accidentally sent 30 years into the past in a time-traveling DeLorean."},
    {"title": "The Terminator", "category": "Sci-Fi", "year": 1984, "rating": 8.0, "description": "A cyborg assassin is sent back in time to kill the mother of a resistance leader."},
    {"title": "Blade Runner 2049", "category": "Sci-Fi", "year": 2017, "rating": 8.0, "description": "A young blade runner discovers a secret that threatens civilization."},
    {"title": "La La Land", "category": "Romance", "year": 2016, "rating": 8.0, "description": "A jazz musician and actress fall in love while pursuing their dreams in LA."},
    {"title": "Get Out", "category": "Horror", "year": 2017, "rating": 7.7, "description": "A Black man visits his white girlfriend's family estate only to discover sinister truths."},
    {"title": "A Quiet Place", "category": "Horror", "year": 2018, "rating": 7.5, "description": "A family struggles to survive in a post-apocalyptic world inhabited by blind monsters."},
    {"title": "Hereditary", "category": "Horror", "year": 2018, "rating": 7.3, "description": "A grieving family is haunted by disturbing occurrences after a death."},
    {"title": "The Grand Budapest Hotel", "category": "Comedy", "year": 2014, "rating": 8.1, "description": "A concierge and his employee become entwined in the theft of a painting."},
    {"title": "Knives Out", "category": "Thriller", "year": 2019, "rating": 7.9, "description": "A detective investigates the death of the patriarch of an eccentric family."},
    {"title": "Coco", "category": "Animation", "year": 2017, "rating": 8.4, "description": "A boy is transported to the Land of the Dead to find his musician great-great-grandfather."},
    {"title": "Spider-Man: Into the Spider-Verse", "category": "Animation", "year": 2018, "rating": 8.4, "description": "A teenager becomes Spider-Man and meets alternate Spider-People."},
    {"title": "Toy Story", "category": "Animation", "year": 1995, "rating": 8.3, "description": "A cowboy doll is threatened when a new toy arrives."},
    {"title": "WALL-E", "category": "Animation", "year": 2008, "rating": 8.4, "description": "A robot falls in love and helps save humanity."},
    {"title": "Up", "category": "Animation", "year": 2009, "rating": 8.2, "description": "A 78-year-old widower sets out to fulfill his dream by tying thousands of balloons to his house."},
    {"title": "Inside Out", "category": "Animation", "year": 2015, "rating": 8.1, "description": "Emotions personified inside the mind of a young girl."},
    {"title": "Gone Girl", "category": "Thriller", "year": 2014, "rating": 8.1, "description": "When a woman goes missing, her husband becomes a suspect."},
    {"title": "No Country for Old Men", "category": "Thriller", "year": 2007, "rating": 8.2, "description": "A hunter stumbles upon drug money and is pursued by a psychopathic hitman."},
    {"title": "Mad Max: Fury Road", "category": "Action", "year": 2015, "rating": 8.1, "description": "A woman rebels against a tyrannical ruler in a post-apocalyptic wasteland."},
    {"title": "John Wick", "category": "Action", "year": 2014, "rating": 7.4, "description": "An ex-hitman comes out of retirement to track down gangsters."},
    {"title": "Mission: Impossible – Fallout", "category": "Action", "year": 2018, "rating": 7.7, "description": "Ethan Hunt and his team race to prevent a nuclear attack."},
    {"title": "Black Panther", "category": "Action", "year": 2018, "rating": 7.3, "description": "T'Challa returns to Wakanda to take his rightful place as king."},
    {"title": "Before Sunrise", "category": "Romance", "year": 1995, "rating": 8.1, "description": "A young man and woman spend one romantic night in Vienna."},
    {"title": "Eternal Sunshine of the Spotless Mind", "category": "Romance", "year": 2004, "rating": 8.3, "description": "A couple erases memories of each other after a painful breakup."},
    {"title": "Her", "category": "Romance", "year": 2013, "rating": 8.0, "description": "A man develops a relationship with an intelligent computer operating system."},
    {"title": "Amélie", "category": "Romance", "year": 2001, "rating": 8.3, "description": "A shy waitress decides to change the lives of those around her for the better."},
    {"title": "The Notebook", "category": "Romance", "year": 2004, "rating": 7.8, "description": "A poor but passionate young man falls in love with a rich girl."},
    {"title": "Catch Me If You Can", "category": "Comedy", "year": 2002, "rating": 8.1, "description": "An FBI agent makes it his mission to capture con artist Frank Abagnale Jr."},
    {"title": "The Big Lebowski", "category": "Comedy", "year": 1998, "rating": 8.1, "description": "A slacker is drawn into a complicated web of events after a case of mistaken identity."},
    {"title": "Superbad", "category": "Comedy", "year": 2007, "rating": 7.6, "description": "Two co-dependent high school seniors try to attend a party before graduation."},
    {"title": "The Hangover", "category": "Comedy", "year": 2009, "rating": 7.7, "description": "Three friends wake up after a bachelor party with no memory and a missing groom."},
    {"title": "Bridesmaids", "category": "Comedy", "year": 2011, "rating": 6.8, "description": "Competition between the maid of honor and a bridesmaid threatens a friendship."},
    {"title": "Game Night", "category": "Comedy", "year": 2018, "rating": 7.0, "description": "A group's weekly game night goes awry when a real kidnapping occurs."},
    {"title": "Free Solo", "category": "Documentary", "year": 2018, "rating": 8.2, "description": "Alex Honnold attempts to free solo climb El Capitan in Yosemite."},
    {"title": "Making a Murderer", "category": "Documentary", "year": 2015, "rating": 8.6, "description": "A true crime documentary about Steven Avery and Brendan Dassey."},
    {"title": "The Act of Killing", "category": "Documentary", "year": 2012, "rating": 8.2, "description": "Former Indonesian death squad leaders reenact their mass killings."},
    {"title": "Amy", "category": "Documentary", "year": 2015, "rating": 7.8, "description": "The life and career of British singer Amy Winehouse."},
    {"title": "Harry Potter and the Sorcerer's Stone", "category": "Fantasy", "year": 2001, "rating": 7.6, "description": "A boy discovers he is a wizard and enrolls in Hogwarts School of Witchcraft."},
    {"title": "The Lord of the Rings: The Two Towers", "category": "Fantasy", "year": 2002, "rating": 8.8, "description": "While Frodo and Sam edge closer to Mordor, the separated fellowship makes new allies."},
    {"title": "Pan's Labyrinth", "category": "Fantasy", "year": 2006, "rating": 8.2, "description": "A girl in post-Civil War Spain escapes into a fantastical labyrinth."},
    {"title": "The Princess Bride", "category": "Fantasy", "year": 1987, "rating": 8.1, "description": "A bedridden boy's grandfather reads him a story of fencing, giants, and True Love."},
    {"title": "Seven Samurai", "category": "Drama", "year": 1954, "rating": 8.6, "description": "Farmers hire seven samurai to protect their village from bandits."},
    {"title": "2001: A Space Odyssey", "category": "Sci-Fi", "year": 1968, "rating": 8.3, "description": "Humanity encounters a mysterious monolith that affects evolution."},
    {"title": "Arrival", "category": "Sci-Fi", "year": 2016, "rating": 7.9, "description": "A linguist works to communicate with extraterrestrial visitors."},
    {"title": "Ex Machina", "category": "Sci-Fi", "year": 2014, "rating": 7.7, "description": "A programmer is selected to participate in a groundbreaking experiment with an AI humanoid."},
    {"title": "Dune", "category": "Sci-Fi", "year": 2021, "rating": 8.0, "description": "Paul Atreides leads nomadic tribes in a revolt against an evil galactic emperor."},
    {"title": "Tenet", "category": "Sci-Fi", "year": 2020, "rating": 7.3, "description": "A secret agent embarks on a mission through a world of time inversion."},
    {"title": "Heat", "category": "Crime", "year": 1995, "rating": 8.3, "description": "A group of professional bank robbers start to feel the heat from police."},
    {"title": "The Usual Suspects", "category": "Crime", "year": 1995, "rating": 8.5, "description": "A sole survivor tells the twisted events leading up to a horrific gun battle."},
    {"title": "Zodiac", "category": "Crime", "year": 2007, "rating": 7.7, "description": "A San Francisco cartoonist becomes obsessed with the Zodiac Killer."},
    {"title": "True Grit", "category": "Western", "year": 2010, "rating": 7.6, "description": "A stubborn teenager enlists a tough U.S. Marshal to track her father's killer."},
    {"title": "Django Unchained", "category": "Western", "year": 2012, "rating": 8.4, "description": "A freed slave teams with a bounty hunter to rescue his wife from a cruel plantation."},
    {"title": "There Will Be Blood", "category": "Drama", "year": 2007, "rating": 8.2, "description": "A story of family, greed, religion, and oil in California at the turn of the 20th century."},
    {"title": "Dunkirk", "category": "War", "year": 2017, "rating": 7.8, "description": "Allied soldiers are evacuated from the beaches of Dunkirk during WWII."},
    {"title": "Full Metal Jacket", "category": "War", "year": 1987, "rating": 8.3, "description": "A pragmatic U.S. Marine observes the dehumanizing effects of the Vietnam war."},
    {"title": "The Hurt Locker", "category": "War", "year": 2008, "rating": 7.5, "description": "An elite Army bomb squad struggles under intense psychological pressure."},
    {"title": "Joker", "category": "Crime", "year": 2019, "rating": 8.4, "description": "A failed comedian becomes the criminal mastermind known as the Joker."},
    {"title": "1917", "category": "War", "year": 2019, "rating": 8.2, "description": "Two British soldiers are given an impossible mission to cross enemy territory."},
    {"title": "Us", "category": "Horror", "year": 2019, "rating": 6.8, "description": "A family is terrorized by doppelgängers."},
    {"title": "Midsommar", "category": "Horror", "year": 2019, "rating": 7.1, "description": "A couple travel to Sweden to visit a rural hometown's midsummer festival."},
    {"title": "The Witch", "category": "Horror", "year": 2015, "rating": 6.9, "description": "A family in 1630s New England is torn apart by the forces of witchcraft."},
    {"title": "Moonlight", "category": "Drama", "year": 2016, "rating": 7.4, "description": "A young African-American man grapples with his identity and sexuality."},
    {"title": "La Haine", "category": "Drama", "year": 1995, "rating": 8.0, "description": "24 hours in the lives of three young men in the impoverished suburbs of Paris."},
    {"title": "City of God", "category": "Crime", "year": 2002, "rating": 8.6, "description": "Two boys grow up in a violent neighborhood in Rio de Janeiro."},
    {"title": "Oldboy", "category": "Thriller", "year": 2003, "rating": 8.4, "description": "A man imprisoned for 15 years seeks revenge on his captor."},
    {"title": "Memento", "category": "Thriller", "year": 2000, "rating": 8.4, "description": "A man with short-term memory loss attempts to track down his wife's murderer."},
    {"title": "Se7en", "category": "Thriller", "year": 1995, "rating": 8.6, "description": "Two detectives hunt a serial killer who uses the seven deadly sins as motives."},
    {"title": "Requiem for a Dream", "category": "Drama", "year": 2000, "rating": 8.3, "description": "The drug-induced dreams of four ambitious people are shattered."},
    {"title": "A Beautiful Mind", "category": "Drama", "year": 2001, "rating": 8.2, "description": "The story of John Nash, a math prodigy who overcomes paranoid schizophrenia."},
    {"title": "Big Fish", "category": "Fantasy", "year": 2003, "rating": 8.0, "description": "A son tries to learn more about his dying father by reliving his fantastical stories."},
    {"title": "Soul", "category": "Animation", "year": 2020, "rating": 8.1, "description": "A jazz musician tries to return to his life after finding himself in the Great Before."},
    {"title": "Ratatouille", "category": "Animation", "year": 2007, "rating": 8.1, "description": "A rat dreams of becoming a great French chef."},
    {"title": "The Truman Show", "category": "Comedy", "year": 1998, "rating": 8.1, "description": "An insurance salesman discovers his entire life is a reality TV show."},
]

SEGMENTS = ["new", "casual", "active", "power"]
SEGMENT_WEIGHTS = [0.2, 0.3, 0.3, 0.2]

EVENT_TYPES = ["view", "click", "watch", "rate_positive", "rate_negative", "wishlist"]
EVENT_WEIGHTS = {"view": 0.3, "click": 0.5, "watch": 1.0, "rate_positive": 1.5, "rate_negative": -0.5, "wishlist": 0.8}
SEGMENT_INTERACTION_COUNTS = {"new": (1, 3), "casual": (5, 15), "active": (15, 40), "power": (40, 80)}

GENRE_AFFINITY = {
    "action_fan": ["Action", "Sci-Fi", "War"],
    "drama_lover": ["Drama", "Crime", "Thriller"],
    "comedy_fan": ["Comedy", "Romance", "Fantasy"],
    "animation_fan": ["Animation", "Fantasy", "Comedy"],
    "horror_fan": ["Horror", "Thriller", "Crime"],
}


def seed_if_empty() -> None:
    with get_db() as db:
        if db.query(User).count() > 0:
            logger.info("seed_skipped", reason="data already present")
            return

    logger.info("seeding_database")
    rng = random.Random(42)

    with get_db() as db:
        items = []
        for idx, movie in enumerate(MOVIES):
            item = Item(
                external_id=f"movie_{idx + 1:03d}",
                title=movie["title"],
                category=movie["category"],
                attributes_json=json.dumps({
                    "year": movie["year"],
                    "rating": movie["rating"],
                    "description": movie["description"],
                    "genres": [movie["category"]],
                }),
                price=0.0,
                status="active",
            )
            db.add(item)
            items.append(item)
        db.flush()

        users = []
        affinity_keys = list(GENRE_AFFINITY.keys())
        for i in range(50):
            segment = rng.choices(SEGMENTS, weights=SEGMENT_WEIGHTS)[0]
            affinity = rng.choice(affinity_keys)
            preferred_genres = GENRE_AFFINITY[affinity]
            user = User(
                external_id=f"user_{i + 1:03d}",
                segment=segment,
                profile_json=json.dumps({"affinity": affinity, "preferred_genres": preferred_genres}),
            )
            db.add(user)
            users.append(user)
        db.flush()

        now = datetime.now(timezone.utc)
        interactions = []
        for user in users:
            profile = user.profile
            preferred_genres = profile.get("preferred_genres", [])
            min_count, max_count = SEGMENT_INTERACTION_COUNTS[user.segment]
            count = rng.randint(min_count, max_count)

            preferred_items = [it for it in items if it.category in preferred_genres]
            other_items = [it for it in items if it.category not in preferred_genres]

            sampled: list[Item] = []
            if preferred_items:
                n_pref = min(int(count * 0.7), len(preferred_items))
                sampled.extend(rng.sample(preferred_items, n_pref))
            n_other = min(count - len(sampled), len(other_items))
            sampled.extend(rng.sample(other_items, n_other))
            sampled = sampled[:count]

            for item in sampled:
                event_type = rng.choices(EVENT_TYPES, weights=[3, 2, 4, 2, 0.5, 1])[0]
                days_ago = rng.randint(1, 180)
                ts = now - timedelta(days=days_ago, hours=rng.randint(0, 23))
                interaction = Interaction(
                    user_id=user.id,
                    item_id=item.id,
                    event_type=event_type,
                    weight=EVENT_WEIGHTS[event_type],
                    timestamp=ts,
                )
                db.add(interaction)
                interactions.append(interaction)

        db.add(Experiment(
            name="popularity_vs_cf",
            description="Compare popularity baseline against collaborative filtering",
            variants_json=json.dumps({
                "control": {"model": "popularity", "weight": 0.5},
                "treatment": {"model": "collaborative_filtering", "weight": 0.5},
            }),
            allocation=0.5,
            status="running",
        ))
        db.add(Experiment(
            name="cf_vs_ranker",
            description="Compare collaborative filtering against the LightGBM ranker",
            variants_json=json.dumps({
                "control": {"model": "collaborative_filtering", "weight": 0.5},
                "treatment": {"model": "ranker", "weight": 0.5},
            }),
            allocation=0.5,
            status="running",
        ))

    logger.info(
        "seed_complete",
        users=len(users),
        items=len(items),
        interactions=len(interactions),
    )
