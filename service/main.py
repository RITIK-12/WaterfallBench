"""Benchmark service entry point."""

from benchmark_service import BenchmarkServiceApp

from waterfallbench_benchmark_service.benchmark_service import WaterfallBench

app = BenchmarkServiceApp(WaterfallBench)
