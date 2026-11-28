from pyspark.sql import SparkSession

from src.streaming.spark_streaming import create_spark_session


def test_create_spark_session():
    session = create_spark_session()

    try:
        assert isinstance(session, SparkSession)
        assert session.sparkContext.appName == "air-quality-dataops-streaming"
    finally:
        session.stop()
