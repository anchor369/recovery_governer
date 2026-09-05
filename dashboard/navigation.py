PAGE_KEY = "app_page"
REQUESTED_PAGE_KEY = "requested_app_page"
INSPECT_ORDER_KEY = "inspect_order_id"

PAGES = (
    "Overview",
    "Recovery Lab",
    "Merchant Ops",
    "Economics & Policy",
    "System",
)


def initialize_navigation(state):
    state.setdefault(PAGE_KEY, "Overview")


def apply_pending_navigation(state):
    requested_page = state.pop(REQUESTED_PAGE_KEY, None)
    if requested_page is not None:
        state[PAGE_KEY] = requested_page


def navigate_to(state, page, order_id=None):
    if page not in PAGES:
        raise ValueError(f"Unknown page: {page}")
    # Sidebar radio state cannot be mutated after its widget is instantiated.
    # Queue the destination so app.py applies it before the next render.
    state[REQUESTED_PAGE_KEY] = page
    if order_id is not None:
        state[INSPECT_ORDER_KEY] = order_id


def selected_order_id(state):
    return state.get(INSPECT_ORDER_KEY)
