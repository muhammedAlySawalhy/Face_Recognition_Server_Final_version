// Script to hash all plain-text passwords in users.json using bcrypt
// Run this ONCE to migrate your user database to secure password storage

const fs = require('fs');
const path = require('path');
const bcrypt = require('bcryptjs');

const usersPath = path.join(process.env.GUI_DATA, 'users.json');

function hashAllPasswords() {
  if (!fs.existsSync(usersPath)) {
    console.error('users.json not found!');
    process.exit(1);
  }
  const users = JSON.parse(fs.readFileSync(usersPath, 'utf8'));
  let changed = false;
  for (const user of users) {
    // Only hash if not already hashed (bcrypt hashes start with $2)
    if (user.password && !user.password.startsWith('$2')) {
      const hash = bcrypt.hashSync(user.password, 12);
      user.password = hash;
      changed = true;
      console.log(`Password for user ${user.username} hashed.`);
    }
  }
  if (changed) {
    fs.writeFileSync(usersPath, JSON.stringify(users, null, 2));
    console.log('All plain-text passwords have been hashed.');
  } else {
    console.log('No plain-text passwords found. No changes made.');
  }
}

hashAllPasswords();
