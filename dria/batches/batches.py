import json
from typing import List, Dict, Any, Tuple
from dria.constants import TASK_TIMEOUT
from dria.client import Dria
from dria.factory.workflows.template import SingletonTemplate
from dria.models import Task, Model, TaskResult
from dria.datasets.base import DriaDataset
from dria.constants import SCORING_BATCH_SIZE


class ParallelSingletonExecutor:
    def __init__(
        self, dria_client: Dria, singleton: SingletonTemplate, dataset: DriaDataset
    ):
        self.dria = dria_client
        self.singleton = singleton
        self.dataset = dataset
        self.batch_size = SCORING_BATCH_SIZE
        self.instructions: Tuple[List[Task], List[Dict[str, Any]]] = ([], [])
        self.models = [Model.OLLAMA]

        name = self.dataset.name + "_" + self.singleton.__name__
        failed = self.dataset.name + "_" + self.singleton.__name__ + "_failed"
        self.dataset_id = self.dataset.db.create_dataset(
            name, description=self.singleton.__name__
        )
        self.failed_dataset_id = self.dataset.db.create_dataset(
            failed, description=self.singleton.__name__
        )

    def load_instructions(self, inputs: List[Dict[str, Any]]):
        for inp in inputs:
            self.instructions[0].append(self._create_task(inp))
            self.instructions[1].append(inp)

    def set_models(self, models: List[Model]):
        self.models = models

    async def execute_workflows(self) -> List[int]:
        entry_ids = []
        for i in range(0, len(self.instructions[0]), self.batch_size):
            batch = self.instructions[0][i : i + self.batch_size]
            original_inputs = self.instructions[1][i : i + self.batch_size]

            results = await self.dria.execute(batch, timeout=len(batch) * TASK_TIMEOUT)
            try:
                ordered_entries = self._align_results(results, original_inputs)
                entry_ids.extend(
                    self.dataset.db.add_entries(self.dataset_id, ordered_entries)
                )
            except RuntimeError as e:
                failed_data = [
                    {
                        "workflow": b.workflow,
                        "id": b.id,
                        "models": [model.value for model in b.models],
                    }
                    for b in batch
                ]
                self.dataset.db.add_entries(self.failed_dataset_id, failed_data)
        return entry_ids

    def _create_task(self, data: Dict[str, Any]) -> Task:
        workflow_data = self.singleton.create(**data).workflow()
        return Task(workflow=workflow_data, models=self.models)

    def _parse_results(self, results: List[TaskResult]):

        outputs = self.singleton.callback(results)
        return [
            output.model_dump_json(indent=2, exclude_none=True, exclude_unset=True)
            for output in outputs
        ], [json.dumps(r.task_input) for r in results]

    def _align_results(
        self, results: List[TaskResult], original_inputs: List[Dict]
    ) -> List:
        """Align results with original inputs and merge the data."""
        outputs = self.singleton.callback(results)
        parsed_outputs = [
            output.model_dump_json(indent=2, exclude_none=True, exclude_unset=True)
            for output in outputs
        ]
        task_inputs = [r.task_input for r in results]

        # Find common keys between first task input and first original input
        common_keys = set(task_inputs[0].keys()) & set(original_inputs[0].keys())

        # Create lookup dictionaries
        result_lookup = {
            json.dumps({k: d[k] for k in common_keys}): (full_output, task_input)
            for full_output, task_input, d in zip(
                parsed_outputs, task_inputs, task_inputs
            )
        }

        ordered_outputs = []
        for original_input in original_inputs:
            lookup_key = json.dumps({k: original_input[k] for k in common_keys})
            if lookup_key in result_lookup:
                ordered_outputs.append(json.loads(result_lookup[lookup_key][0]))

        return ordered_outputs

    async def run(self):
        return await self.execute_workflows()
