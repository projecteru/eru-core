# pubsub keys
ERU_TASK_PUBKEY = 'eru:task:pub:%s'
ERU_TASK_LOGKEY = 'eru:task:log:%s'
ERU_TASK_RESULTKEY = 'eru:task:result:%s'

ERU_AGENT_CONTAINERSKEY = 'eru:agent:%s:containers'
ERU_AGENT_WATCHERKEY = 'eru:agent:%s:watcher'
ERU_AGENT_DIE_REASON = 'eru:agent:%s:container:reason'

PUB_END_MESSAGE = 'ERU_END_PUB'

OK = 'ok'

# task
TASK_CREATE = 1
TASK_BUILD = 2
TASK_REMOVE = 3
TASK_MIGRATE = 4

TASK_SUCCESS = 1
TASK_FAILED = 2

TASK_ACTIONS = {
    TASK_CREATE: 'create',
    TASK_BUILD: 'build',
    TASK_REMOVE: 'remove',
    TASK_MIGRATE: 'migrate',
}
TASK_RESULTS = {
    TASK_SUCCESS: 'succeeded',
    TASK_FAILED: 'failed',
}

TASK_RESULT_SUCCESS = 'SUCCESS'
TASK_RESULT_FAILED = 'FAILED'
