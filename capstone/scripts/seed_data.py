"""
Seed script to populate the database with sample posts for testing.
Run with: python -m scripts.seed_data
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import init_db, async_session, Post


SAMPLE_POSTS = [
    {
        "title": "The Behavior of Red Foxes",
        "content": "Red foxes (Vulpes vulpes) are the largest of the true foxes. They are highly adaptable animals found across the entire Northern Hemisphere. Known for their intelligence and cunning nature, red foxes have been the subject of folklore for centuries. Their diet consists mainly of rodents, rabbits, birds, and fruit. They are primarily nocturnal and solitary hunters.",
        "category": "animal"
    },
    {
        "title": "Gray Wolf Pack Dynamics",
        "content": "Gray wolves (Canis lupus) are highly social animals that live in family packs. A typical pack consists of a breeding pair and their offspring from previous years. Wolves communicate through howling, body language, and scent marking. They are apex predators and play a crucial role in maintaining ecosystem balance. Their hunting strategies demonstrate remarkable teamwork.",
        "category": "animal"
    },
    {
        "title": "Understanding Canine Companions",
        "content": "Dogs have been domesticated for thousands of years and remain our most loyal companions. From small lap dogs to large working breeds, dogs exhibit incredible diversity. They are known for their ability to understand human emotions and respond to commands. Modern dog breeds range from the tiny Chihuahua to the massive Great Dane.",
        "category": "animal"
    },
    {
        "title": "Brown Bears in the Wild",
        "content": "Brown bears (Ursus arctos) are powerful omnivores found across North America, Europe, and Asia. They hibernate during winter months, surviving on stored fat reserves. Brown bears are excellent fishers, particularly during salmon runs. Despite their size, they can run at speeds up to 35 mph. They are generally solitary except for mothers with cubs.",
        "category": "animal"
    },
    {
        "title": "White-tailed Deer Ecology",
        "content": "White-tailed deer (Odocoileus virginianus) are the most common large animal in North America. They are herbivores that browse on grasses, plants, fruits, and twigs. During fall, males grow antlers which are shed annually. Deer are important prey species for wolves, mountain lions, and bears. They adapt well to suburban environments.",
        "category": "animal"
    },
    {
        "title": "Mountain Landscapes of the World",
        "content": "Mountains cover approximately 22% of the Earth's land surface. They are formed through tectonic forces or volcanic activity. Mountain ecosystems support incredible biodiversity, with different species at various elevations. From the Himalayas to the Andes, mountains have shaped human cultures and continue to inspire awe. They play vital roles in water cycles and climate regulation.",
        "category": "landscape"
    },
    {
        "title": "The Power of Ocean Currents",
        "content": "Ocean currents are continuous movements of seawater driven by wind, temperature, and salinity differences. They distribute heat around the globe, influencing climate patterns. The Gulf Stream carries warm water from the tropics to the North Atlantic, moderating European weather. These currents support marine ecosystems by transporting nutrients and plankton.",
        "category": "landscape"
    },
    {
        "title": "Domestic Cats: Independent Yet Affectionate",
        "content": "Cats (Felis catus) have been human companions for nearly 10,000 years. Unlike dogs, cats retain much of their wild independence. They are skilled hunters with excellent night vision and hearing. Modern domestic cats come in various breeds, from the sleek Siamese to the fluffy Persian. Despite their independent nature, cats form strong bonds with their owners.",
        "category": "animal"
    },
    {
        "title": "Bald Eagles: America's National Bird",
        "content": "The bald eagle (Haliaeetus leucocephalus) is a symbol of American freedom. These magnificent raptors were once endangered but have made a remarkable recovery. Bald eagles primarily eat fish, which they catch with their powerful talons. They build the largest nests of any North American bird, sometimes weighing over a ton. Their distinctive white head and tail make them easily recognizable.",
        "category": "animal"
    },
    {
        "title": "Wild Horses of the American West",
        "content": "Wild horses, or mustangs, roam the western United States in free-roaming herds. These horses are descendants of Spanish colonial horses brought to the Americas in the 16th century. They live in complex social groups led by a dominant mare. The Bureau of Land Management manages their populations through gathers and adoption programs. Wild horses symbolize the spirit of the American frontier.",
        "category": "animal"
    },
    {
        "title": "The Art of Birdwatching",
        "content": "Birdwatching is a popular hobby enjoyed by millions worldwide. Birders identify species by their appearance, songs, and behaviors. Binoculars and field guides are essential tools for this activity. Many birdwatchers contribute to citizen science projects like eBird. The hobby combines outdoor recreation with scientific observation and conservation awareness.",
        "category": "hobby"
    },
    {
        "title": "Forest Ecosystems and Their Importance",
        "content": "Forests cover about 31% of the global land area and are vital for ecological balance. They absorb carbon dioxide, produce oxygen, and regulate water cycles. Forests are home to 80% of terrestrial biodiversity. Tropical rainforests, in particular, contain countless species yet to be discovered. Deforestation remains a critical threat to these essential ecosystems.",
        "category": "landscape"
    }
]


async def seed():
    """Seed the database with sample posts."""
    await init_db()

    async with async_session() as db:
        for post_data in SAMPLE_POSTS:
            post = Post(**post_data)
            db.add(post)

        await db.commit()
        print(f"Seeded {len(SAMPLE_POSTS)} posts")


if __name__ == "__main__":
    asyncio.run(seed())
