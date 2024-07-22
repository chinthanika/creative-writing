from .storage_access import content_download
from .word_counter import count_words

def recalculate_progress(goal_ref, goal_data, user_id):
    goal_type = goal_data.get('goal_type')
    target = goal_data.get('target', 0)
    progress = 0

    if goal_type == "number_of_words":
        content_id = goal_data.get('content_id')
        content = content_download(user_id, content_id)
        word_count = count_words(content)
        progress = (word_count / target) * 100

    elif goal_type == "user_defined":
        task_docs = goal_ref.collection('tasks').stream()
        completed_tasks = sum(1 for task in task_docs if task.to_dict().get('completed'))
        total_tasks = goal_ref.collection('tasks').count().get()[0].to_dict().get('count')
        if total_tasks > 0:
            progress = (completed_tasks / total_tasks) * 100

    return progress