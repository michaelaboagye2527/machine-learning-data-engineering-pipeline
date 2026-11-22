from data_engineering_pipeline.example_code import hello_pipeline


def test_hello_pipeline_multiplies_by_ten():

    assert hello_pipeline(name="test") == [10, 20, 30, 50, 80, 90, 230]
