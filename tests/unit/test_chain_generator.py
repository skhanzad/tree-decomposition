from src.experiments.generators.chain_regions import ChainRegionConfig, build_chain_task
from src.graph.bag_assignment import assign_actions
from src.graph.decomposition import build_decomposition
from src.graph.interaction_graph import build_interaction_graph


def test_chain_task_decomposes_into_linear_bags():
    config = ChainRegionConfig(num_regions=4, local_domain_size=3)
    task = build_chain_task(config)
    decomp = build_decomposition(task, build_interaction_graph(task))
    owned = assign_actions(task, decomp)

    assert len(decomp.bags) == 2 * config.num_regions - 2
    assert all(actions for actions in owned.values())
    assert sum(len(actions) for actions in owned.values()) == len(task.actions)


def test_chain_affected_subtree_grows_toward_early_regions():
    from src.experiments.generators.chain_regions import region_disruption_state_fact
    from src.repair.disruption import StateFactChange
    from src.summaries.invalidation import directly_affected_bags, expand_to_affected_subtree

    config = ChainRegionConfig(num_regions=5, local_domain_size=3)
    task = build_chain_task(config)
    decomp = build_decomposition(task, build_interaction_graph(task))
    owned = assign_actions(task, decomp)

    sizes = []
    for region in range(config.num_regions):
        var, val = region_disruption_state_fact(region, config)
        disruption = StateFactChange(variable=var, new_value=val)
        direct = directly_affected_bags(decomp, owned, disruption)
        subtree = expand_to_affected_subtree(decomp, direct)
        sizes.append(len(subtree))

    assert sizes[-1] < sizes[0]
