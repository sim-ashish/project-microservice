let socket = null;

function openGroup(groupId) {
  // close previous socket
  if (socket) socket.close();

  socket = new WebSocket(`ws://localhost:8000/ws/${groupId}`);

  socket.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    displayMessage(msg);  // show only messages of this group
  };
}
