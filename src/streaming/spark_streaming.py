"""Spark Structured Streaming session setup."""

from pyspark.sql import SparkSession


def create_spark_session() -> SparkSession:
    """Create or retrieve the Spark session for the air quality pipeline."""
    return SparkSession.builder.appName("air-quality-dataops-streaming").getOrCreate()
