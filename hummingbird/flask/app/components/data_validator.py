def validate_goal_type(goal_type):
    if goal_type not in ['number_of_words', 'user_defined']:
        raise ValueError('Invalid goal type. Must be one of: number_of_words, user_defined')