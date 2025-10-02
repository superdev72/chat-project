from django.urls import path

from . import views

app_name = "chat"

urlpatterns = [
    # User management
    path("users/", views.UserListView.as_view(), name="user-list"),
    # Conversation management
    path("conversations/", views.ConversationListView.as_view(), name="conversation-list"),
    path(
        "conversations/<uuid:user_id>/",
        views.conversation_detail_view,
        name="conversation-detail",
    ),
    # Message management
    path(
        "conversations/<uuid:conversation_id>/messages/",
        views.get_messages_view,
        name="get-messages",
    ),
    path(
        "conversations/<uuid:conversation_id>/send/",
        views.send_message_view,
        name="send-message",
    ),
    path("messages/<str:message_id>/", views.delete_message_view, name="delete-message"),
]
