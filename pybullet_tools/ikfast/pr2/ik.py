import random

from ..utils import get_ik_limits, compute_forward_kinematics, compute_inverse_kinematics, select_solution, \
    USE_ALL, USE_CURRENT
from ...pr2_utils import PR2_TOOL_FRAMES, get_torso_arm_joints, get_gripper_link, get_arm_joints
from ...utils import multiply, get_link_pose, link_from_name, get_joint_positions, \
    joint_from_name, invert, get_custom_limits, all_between, sub_inverse_kinematics, set_joint_positions, \
    get_joint_positions, pairwise_collision

IK_FRAME = {
    'left': 'l_gripper_tool_frame',
    'right': 'r_gripper_tool_frame',
}
BASE_FRAME = 'base_link'

TORSO_JOINT = 'torso_lift_joint'
UPPER_JOINT = {
    'left': 'l_upper_arm_roll_joint',
    'right': 'r_upper_arm_roll_joint',
}

#####################################

def get_tool_pose(robot, arm):
    from .ikLeft import leftFK
    from .ikRight import rightFK
    arm_fk = {'left': leftFK, 'right': rightFK}
    # TODO: compute static transform from base_footprint -> base_link
    ik_joints = get_torso_arm_joints(robot, arm)
    conf = get_joint_positions(robot, ik_joints)
    assert len(conf) == 8
    base_from_tool = compute_forward_kinematics(arm_fk[arm], conf)
    #quat = quat if quat.real >= 0 else -quat  # solves q and -q being same rotation
    world_from_base = get_link_pose(robot, link_from_name(robot, BASE_FRAME))
    return multiply(world_from_base, base_from_tool)

#####################################

def is_ik_compiled():
    try:
        from .ikLeft import leftIK
        from .ikRight import rightIK
        return True
    except ImportError:
        return False

def get_ik_generator(robot, arm, ik_pose, torso_limits=USE_CURRENT, upper_limits=USE_CURRENT, custom_limits={}):
    from .ikLeft import leftIK
    from .ikRight import rightIK
    arm_ik = {'left': leftIK, 'right': rightIK}
    world_from_base = get_link_pose(robot, link_from_name(robot, BASE_FRAME))
    base_from_ik = multiply(invert(world_from_base), ik_pose)
    sampled_limits = [get_ik_limits(robot, joint_from_name(robot, name), limits) for name, limits in
                      [(TORSO_JOINT, torso_limits), (UPPER_JOINT[arm], upper_limits)]]
    arm_joints = get_torso_arm_joints(robot, arm)

    lower_limits, upper_limits = get_custom_limits(robot, arm_joints, custom_limits)
    while True:
        sampled_values = [random.uniform(*limits) for limits in sampled_limits]
        confs = compute_inverse_kinematics(arm_ik[arm], base_from_ik, sampled_values)
        solutions = [q for q in confs if all_between(lower_limits, q, upper_limits)]
        yield solutions
        if all(lower == upper for lower, upper in sampled_limits):
            break

def get_tool_from_ik(robot, arm):
    # TODO: change PR2_TOOL_FRAMES[arm] to be IK_LINK[arm]
    world_from_tool = get_link_pose(robot, link_from_name(robot, PR2_TOOL_FRAMES[arm]))
    world_from_ik = get_link_pose(robot, link_from_name(robot, IK_FRAME[arm]))
    return multiply(invert(world_from_tool), world_from_ik)

def sample_tool_ik(robot, arm, tool_pose, nearby_conf=USE_ALL, max_attempts=25, **kwargs):
    ik_pose = multiply(tool_pose, get_tool_from_ik(robot, arm))
    generator = get_ik_generator(robot, arm, ik_pose, **kwargs)
    arm_joints = get_torso_arm_joints(robot, arm)
    for _ in range(max_attempts):
        try:
            solutions = next(generator)
            # TODO: sort by distance from the current solution when attempting?
            if solutions:
                return select_solution(robot, arm_joints, solutions, nearby_conf=nearby_conf)
        except StopIteration:
            break
    return None

def pr2_inverse_kinematics(robot, arm, gripper_pose, upper_limits=USE_ALL, obstacles=[], custom_limits={}, **kwargs):
    arm_link = get_gripper_link(robot, arm)
    arm_joints = get_arm_joints(robot, arm)
    if is_ik_compiled():
        ik_joints = get_torso_arm_joints(robot, arm)
        torso_arm_conf = sample_tool_ik(robot, arm, gripper_pose, custom_limits=custom_limits,
                                        torso_limits=USE_CURRENT, upper_limits=upper_limits, **kwargs)
        if torso_arm_conf is None:
            return None
        set_joint_positions(robot, ik_joints, torso_arm_conf)
        arm_conf = get_joint_positions(robot, arm_joints)
    else:
        arm_conf = sub_inverse_kinematics(robot, arm_joints[0], arm_link, gripper_pose, custom_limits=custom_limits)
    if (arm_conf is None) or any(pairwise_collision(robot, b) for b in obstacles):
        return None
    return arm_conf
