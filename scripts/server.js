const express = require("express")
const { createServer } = require("http")
const { Server } = require("socket.io")
const cors = require("cors")

const app = express()
const server = createServer(app)

// Universal CORS configuration that works with any tunneling service
const getAllowedOrigins = () => {
  const origins = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"]

  // Add environment-specific origins
  if (process.env.FRONTEND_URL) {
    origins.push(process.env.FRONTEND_URL)
  }

  // In development, allow common tunneling services
  if (process.env.NODE_ENV !== "production") {
    return (origin, callback) => {
      // Allow requests with no origin (mobile apps, Postman, etc.)
      if (!origin) return callback(null, true)

      // Allow localhost
      if (origin.includes("localhost") || origin.includes("127.0.0.1")) {
        return callback(null, true)
      }

      // Allow common tunneling services
      const tunnelPatterns = [
        /https:\/\/.*\.ngrok-free\.app/,
        /https:\/\/.*\.ngrok\.io/,
        /https:\/\/.*\.ngrok\.app/,
        /https:\/\/.*\.cloudflare\.com/,
        /https:\/\/.*\.trycloudflare\.com/,
        /https:\/\/.*\.loca\.lt/,
        /https:\/\/.*\.serveo\.net/,
        /https:\/\/.*\.pagekite\.me/,
      ]

      const isAllowed = tunnelPatterns.some((pattern) => pattern.test(origin))
      callback(null, isAllowed)
    }
  }

  return origins
}

// Configure CORS for Express
app.use(
  cors({
    origin: getAllowedOrigins(),
    credentials: true,
  }),
)

// Configure Socket.IO with universal CORS
const io = new Server(server, {
  cors: {
    origin: getAllowedOrigins(),
    methods: ["GET", "POST"],
    credentials: true,
  },
  transports: ["websocket", "polling"],
  allowEIO3: true,
})

app.use(express.json())

// Health check endpoint
app.get("/health", (req, res) => {
  res.json({
    status: "ok",
    rooms: rooms.size,
    timestamp: new Date().toISOString(),
    environment: process.env.NODE_ENV || "development",
    port: process.env.PORT || 3001,
  })
})

// Store room data
const rooms = new Map()

// Socket.IO connection handling
io.on("connection", (socket) => {
  const clientIP = socket.handshake.headers["x-forwarded-for"] || socket.handshake.address
  const userAgent = socket.handshake.headers["user-agent"]
  console.log(`User connected: ${socket.id} from IP: ${clientIP}`)
  console.log(`User Agent: ${userAgent}`)

  // Handle joining a room
  socket.on("join-room", ({ roomCode, userName, webtoonUrl }) => {
    console.log(`User ${userName} (${socket.id}) joining room ${roomCode}`)

    // Leave any existing rooms
    socket.rooms.forEach((room) => {
      if (room !== socket.id) {
        socket.leave(room)
      }
    })

    // Join the new room
    socket.join(roomCode)

    // Store user data
    socket.userData = { userName, roomCode, webtoonUrl }

    // Initialize room if it doesn't exist
    if (!rooms.has(roomCode)) {
      rooms.set(roomCode, {
        users: new Map(),
        messages: [],
        webtoonUrl: webtoonUrl,
        reactions: {},
        createdAt: Date.now(),
      })
    }

    const room = rooms.get(roomCode)

    // Update room URL if this is the first user or room creator
    if (room.users.size === 0) {
      room.webtoonUrl = webtoonUrl
    }

    room.users.set(socket.id, { id: socket.id, userName })

    // Send current room data to the new user
    const roomUsers = Array.from(room.users.values())
    socket.emit("room-users", roomUsers)
    socket.emit("webtoon-url-update", { url: room.webtoonUrl })
    socket.emit("reaction-update", room.reactions)

    // Send recent messages to new user
    const recentMessages = room.messages.slice(-50)
    recentMessages.forEach((msg) => {
      socket.emit("chat-message", msg)
    })

    // Notify others about the new user
    socket.to(roomCode).emit("user-joined", { id: socket.id, userName })
    socket.to(roomCode).emit("room-users", roomUsers)

    console.log(`Room ${roomCode} now has ${roomUsers.length} users`)
  })

  // Handle scroll updates
  socket.on("scroll-update", ({ roomCode, scrollTop }) => {
    socket.to(roomCode).emit("scroll-sync", { scrollTop })
  })

  // Handle chat messages
  socket.on("chat-message", ({ roomCode, message }) => {
    const messageWithId = {
      ...message,
      id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
    }

    const room = rooms.get(roomCode)
    if (room) {
      room.messages.push(messageWithId)
      if (room.messages.length > 100) {
        room.messages = room.messages.slice(-100)
      }
    }

    io.to(roomCode).emit("chat-message", messageWithId)
  })

  // Handle reactions
  socket.on("reaction", ({ roomCode, reactionType, userName }) => {
    const room = rooms.get(roomCode)
    if (!room) return

    if (!room.reactions[reactionType]) {
      room.reactions[reactionType] = {
        type: reactionType,
        emoji: getEmojiForReaction(reactionType),
        count: 0,
        users: [],
      }
    }

    const reaction = room.reactions[reactionType]
    const userIndex = reaction.users.indexOf(userName)

    if (userIndex > -1) {
      reaction.users.splice(userIndex, 1)
      reaction.count = Math.max(0, reaction.count - 1)
    } else {
      reaction.users.push(userName)
      reaction.count += 1
    }

    if (reaction.count === 0) {
      delete room.reactions[reactionType]
    }

    io.to(roomCode).emit("reaction-update", room.reactions)

    const reactionMessage = {
      id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
      userName: "System",
      message: `${userName} reacted with ${reaction.emoji}`,
      timestamp: Date.now(),
      type: "reaction",
    }

    room.messages.push(reactionMessage)
    io.to(roomCode).emit("chat-message", reactionMessage)
  })

  // Handle leaving a room
  socket.on("leave-room", ({ roomCode }) => {
    handleUserLeave(socket, roomCode)
  })

  // Handle disconnection
  socket.on("disconnect", (reason) => {
    console.log(`User disconnected: ${socket.id}, reason: ${reason}`)
    if (socket.userData) {
      handleUserLeave(socket, socket.userData.roomCode)
    }
  })
})

function getEmojiForReaction(reactionType) {
  const emojiMap = {
    heart: "❤️",
    laugh: "😂",
    thumbsup: "👍",
    angry: "😠",
    sad: "😢",
  }
  return emojiMap[reactionType] || "👍"
}

function handleUserLeave(socket, roomCode) {
  if (!roomCode) return

  const room = rooms.get(roomCode)
  if (room && room.users.has(socket.id)) {
    const user = room.users.get(socket.id)
    room.users.delete(socket.id)

    // Remove user from all reactions
    Object.keys(room.reactions).forEach((reactionType) => {
      const reaction = room.reactions[reactionType]
      const userIndex = reaction.users.indexOf(user.userName)
      if (userIndex > -1) {
        reaction.users.splice(userIndex, 1)
        reaction.count = Math.max(0, reaction.count - 1)
        if (reaction.count === 0) {
          delete room.reactions[reactionType]
        }
      }
    })

    socket.to(roomCode).emit("user-left", user)

    const roomUsers = Array.from(room.users.values())
    socket.to(roomCode).emit("room-users", roomUsers)
    socket.to(roomCode).emit("reaction-update", room.reactions)

    if (room.users.size === 0) {
      rooms.delete(roomCode)
      console.log(`Room ${roomCode} deleted (empty)`)
    }

    console.log(`User ${user.userName} left room ${roomCode}`)
  }

  socket.leave(roomCode)
}

// Get room info endpoint
app.get("/room/:roomCode", (req, res) => {
  const { roomCode } = req.params
  const room = rooms.get(roomCode)

  if (room) {
    res.json({
      roomCode,
      userCount: room.users.size,
      users: Array.from(room.users.values()),
      messageCount: room.messages.length,
      contentUrl: room.webtoonUrl,
      reactions: room.reactions,
      createdAt: room.createdAt,
    })
  } else {
    res.status(404).json({ error: "Room not found" })
  }
})

const PORT = process.env.PORT || 3001

server.listen(PORT, () => {
  console.log(`Socket.IO server running on port ${PORT}`)
  console.log(`Environment: ${process.env.NODE_ENV || "development"}`)
  console.log(`CORS configured for universal tunneling service support`)
})

// Graceful shutdown
process.on("SIGTERM", () => {
  console.log("SIGTERM received, shutting down gracefully")
  server.close(() => {
    console.log("Server closed")
    process.exit(0)
  })
})
