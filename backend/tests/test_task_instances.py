def test_generate_task_instances_for_date(client, auth_headers):

  response = client.post(
        f"/tasks_instances/generate",
        headers=auth_headers,
        json={
            "date_instance":"2026-04-16"
          }
    )

  print(response.status_code)
  print(response.json())

  assert response.status_code in (201,200)


def test_complete_task_instance(client, auth_headers, task_instance):

  response = client.post(
        f"/task_instances/{task_instance['id']}/complete",
        headers=auth_headers,
        json={
            "completion_level":"normal"
          }
    )

  print(response.status_code)
  print(response.json())

  assert response.status_code == 200