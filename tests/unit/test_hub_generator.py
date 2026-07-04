from src.experiments.generators.hub_regions import HubRegionConfig, build_hub_task
from src.graph.bag_assignment import assign_actions
from src.graph.decomposition import build_decomposition
from src.graph.interaction_graph import build_interaction_graph
from src.repair.disruption import StateFactChange
from src.summaries.invalidation import directly_affected_bags, expand_to_affected_subtree


def test_hub_task_has_star_decomposition_with_worker_leaves():
    config = HubRegionConfig(num_workers=4, local_domain_size=3)
    task = build_hub_task(config)
    decomp = build_decomposition(task, build_interaction_graph(task))
    owned = assign_actions(task, decomp)

    root = decomp.bag(decomp.root_id)
    assert "goal_robot" in root.variables
    assert len(root.children_ids) == config.num_workers
    assert sum(len(actions) for actions in owned.values()) == len(task.actions)


def test_hub_disruption_invalidates_only_one_leaf_and_root():
    config = HubRegionConfig(num_workers=4, local_domain_size=3)
    task = build_hub_task(config)
    decomp = build_decomposition(task, build_interaction_graph(task))
    owned = assign_actions(task, decomp)

    disruption = StateFactChange(variable="worker_1", new_value="w1")
    direct = directly_affected_bags(decomp, owned, disruption)
    subtree = expand_to_affected_subtree(decomp, direct)

    assert len(subtree) == 2
    assert decomp.root_id in subtree
