import project

def test_validate_record_success():
    record = {
        "timestamp": "2024-01-01T12:00:00Z",
        "metric": "weight_lb",
        "value": 80000,
        "source": "IND570_scale_01",
    }
    assert project.validate_record(record) is None


def test_validate_record_sensor_error():
    record = {
        "timestamp": "2024-01-01T12:00:00Z",
        "metric": "weight_lb",
        "value": 150000,
        "source": "IND570_scale_01",
    }
    assert project.validate_record(record) == "sensor_error_out_of_range"


def test_analyze_critical_event():
    records = [{
        "timestamp": "2024-01-01T12:00:00Z",
        "metric": "weight_lb",
        "value": 98000,
        "source": "IND570_scale_01",
    }]
    analysis = project.analyze_data(records)
    assert len(analysis["criticals"]) == 1


def test_system_health_escalation():
    valid = [{}] * 65
    invalid = [{}] * 35
    health = project.evaluate_system_health(valid, invalid)
    assert health["escalate"] is True
