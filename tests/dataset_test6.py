import json
from dria import DriaDataset, DatasetGenerator, Model
from dria.factory.search import SearchWeb
import asyncio

my_dataset = DriaDataset(
    name="searches",
    description="A dataset for pages",
    schema=SearchWeb.OutputSchema,
)

generator = DatasetGenerator(dataset=my_dataset)


instructions = [
    {"query": "Istanbul'daki en iyi kebapçılar", "lang": "tr", "n_results": 5},
    {"query": "Best kebap places in Istanbul", "lang": "en", "n_results": 5},
]

asyncio.run(
    generator.generate_data(
        instructions=instructions,
        singletons=SearchWeb,
        models=[Model.OLLAMA],
    )
)


my_dataset.to_jsonl()
