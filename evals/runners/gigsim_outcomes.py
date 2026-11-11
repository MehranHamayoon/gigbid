from gigsim.service import CLIENTS, predicted_outcome


def outcome(job, text, amount):
    return predicted_outcome(job, CLIENTS[job["client_id"]], text, amount)
