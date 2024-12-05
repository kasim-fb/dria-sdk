import json
from dria import DriaDataset, DatasetGenerator, Model
from dria.factory.persona import PersonaBio
import asyncio

my_dataset = DriaDataset(
    name="pages",
    description="A dataset for pages",
    schema=PersonaBio[-1].OutputSchema,
)

generator = DatasetGenerator(dataset=my_dataset)


instructions = [
    {
        "simulation_description": "A medieval village in northern britain",
        "num_of_samples": 8,
    },
    {"simulation_description": "A modern neo-tokio", "num_of_samples": 5},
]

asyncio.run(
    generator.generate_data(
        instructions=instructions,
        singletons=PersonaBio,
        models=[Model.ANTHROPIC_HAIKU_3_5_OR, Model.QWEN2_5_72B_OR],
    )
)


my_dataset.to_jsonl()
