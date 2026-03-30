const fs = require('fs');
const path = require('path');

function testReadmeContent() {
  const readmePath = path.join(__dirname, '..', 'README.md');
  const content = fs.readFileSync(readmePath, 'utf8');
  
  // Check for Linux and macOS mentions with "coming soon"
  const hasLinuxComingSoon = /Linux.*[Cc]oming [Ss]oon/.test(content);
  const hasMacOSComingSoon = /macOS.*[Cc]oming [Ss]oon/.test(content);
  
  console.log('Testing README content...');
  console.log('Has Linux coming soon:', hasLinuxComingSoon);
  console.log('Has macOS coming soon:', hasMacOSComingSoon);
  
  if (!hasLinuxComingSoon || !hasMacOSComingSoon) {
    console.error('FAIL: README should clarify Linux/macOS status as "coming soon"');
    console.error('Current content may not have the expected phrases.');
    process.exit(1);
  } else {
    console.log('PASS: README correctly mentions Linux/macOS as coming soon');
    process.exit(0);
  }
}

if (require.main === module) {
  testReadmeContent();
}
