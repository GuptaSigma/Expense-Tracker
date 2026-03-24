/**
 * Google Apps Script Email Service for ExpenseTracker OTP
 * 
 * SETUP INSTRUCTIONS:
 * 1. Go to https://script.google.com
 * 2. Create new project
 * 3. Paste this code
 * 4. Deploy > New deployment > Type: Web app
 * 5. Execute as: Me
 * 6. Who has access: Anyone
 * 7. Copy deployment URL
 * 8. Add to .env: APPS_SCRIPT_URL=<your-deployment-url>
 */

function doPost(e) {
  try {
    // Parse incoming JSON data
    const data = JSON.parse(e.postData.contents);
    const email = data.email;
    const otp = data.otp;
    const username = data.username;
    
    // Validate input
    if (!email || !otp || !username) {
      return ContentService.createTextOutput(JSON.stringify({
        success: false,
        error: "Missing required fields"
      })).setMimeType(ContentService.MimeType.JSON);
    }
    
    // Email subject
    const subject = "ExpenseTracker - OTP Verification";
    
    // HTML email body
    const htmlBody = `
      <html>
        <body style="font-family: 'Plus Jakarta Sans', Arial, sans-serif; background-color: #f8fafc; padding: 20px; margin: 0;">
          <div style="max-width: 600px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <div style="text-align: center; margin-bottom: 30px;">
              <h1 style="color: #0f172a; margin: 0; font-size: 28px;">💰 ExpenseTracker</h1>
              <p style="color: #64748b; margin: 10px 0 0 0; font-size: 16px;">Verify Your Email</p>
            </div>

            <div style="margin-bottom: 30px;">
              <p style="color: #334155; font-size: 16px; margin-bottom: 20px;">Hi <strong>${username}</strong>,</p>
              <p style="color: #334155; font-size: 16px; margin-bottom: 20px;">Thank you for signing up! To complete your registration, please verify your email using the OTP below:</p>

              <div style="background: #f1f5f9; border: 2px solid #e2e8f0; border-radius: 8px; padding: 20px; text-align: center; margin: 30px 0;">
                <p style="color: #1e293b; font-size: 36px; font-weight: bold; margin: 0; letter-spacing: 10px; font-family: 'Courier New', monospace;">${otp}</p>
              </div>

              <p style="color: #94a3b8; font-size: 14px; margin-top: 20px;">⏰ This OTP will expire in <strong>10 minutes</strong>.</p>
            </div>

            <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; border-radius: 4px; margin: 20px 0;">
              <p style="color: #92400e; margin: 0; font-size: 14px;">
                <strong>⚠️ Security Tip:</strong> Never share your OTP with anyone. ExpenseTracker will never ask for your OTP via phone or email.
              </p>
            </div>

            <div style="border-top: 1px solid #e2e8f0; padding-top: 20px; margin-top: 30px; text-align: center;">
              <p style="color: #94a3b8; font-size: 12px; margin: 5px 0;">If you didn't sign up for this account, please ignore this email.</p>
              <p style="color: #94a3b8; font-size: 12px; margin: 10px 0 0 0;">© ${new Date().getFullYear()} ExpenseTracker. All rights reserved.</p>
            </div>
          </div>
        </body>
      </html>
    `;
    
    // Plain text version (fallback)
    const plainBody = `
Hi ${username},

Thank you for signing up for ExpenseTracker!

Your OTP verification code is: ${otp}

This OTP will expire in 10 minutes.

If you didn't sign up for this account, please ignore this email.

© ${new Date().getFullYear()} ExpenseTracker
    `;
    
    // Send email using Gmail
    MailApp.sendEmail({
      to: email,
      subject: subject,
      body: plainBody,
      htmlBody: htmlBody,
      name: "ExpenseTracker"
    });
    
    // Log success
    Logger.log(`✅ OTP email sent to ${email}`);
    
    // Return success response
    return ContentService.createTextOutput(JSON.stringify({
      success: true,
      message: "OTP email sent successfully"
    })).setMimeType(ContentService.MimeType.JSON);
    
  } catch (error) {
    // Log error
    Logger.log(`❌ Error: ${error.toString()}`);
    
    // Return error response
    return ContentService.createTextOutput(JSON.stringify({
      success: false,
      error: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

// Test function (optional - for testing in Apps Script editor)
function testSendEmail() {
  const testData = {
    email: "sagargupta585845@gmail.com",
    otp: "123456",
    username: "Test User"
  };
  
  const result = doPost({
    postData: {
      contents: JSON.stringify(testData)
    }
  });
  
  Logger.log(result.getContent());
}
