"""Check a data root against the service's data contract: python -m waterfallbench_benchmark_service.validate"""

import sys

from waterfallbench_benchmark_service.data import build_datasets, data_root, load_task_infos, validate_data_root


def main() -> int:
    root = data_root()
    problems = validate_data_root(root)
    infos, _ = load_task_infos(root)
    counts = ", ".join(f"{name}={len(tasks)}" for name, tasks in build_datasets(infos).items())
    print(f"{root}: {counts}")
    for problem in problems:
        print(f"PROBLEM {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
