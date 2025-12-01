import { TIMEOUT_SECONDS } from "./config";

const timeout = function (s) {
  return new Promise(function (_, reject) {
    setTimeout(function () {
      reject(new Error(`Request took too long! Timeout after ${s} second`));
    }, s * 1000);
  });
};

export const getJSON = async function (url) {
  try {
    const res = await Promise.race([fetch(url), timeout(TIMEOUT_SECONDS)]);
    
    // Check if response is ok before parsing JSON
    if (!res.ok) {
      let errorMessage = `Server error: ${res.status}`;
      try {
        const errorData = await res.json();
        errorMessage = errorData.data || errorData.message || errorMessage;
      } catch (e) {
        // If JSON parsing fails, use status text
        errorMessage = res.statusText || errorMessage;
      }
      throw new Error(errorMessage);
    }
    
    const data = await res.json();
    return data;
  } catch (err) {
    // Provide more helpful error messages
    if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
      throw new Error('Unable to connect to the server. Please make sure the Flask backend is running on http://127.0.0.1:5000');
    } else if (err.message.includes('timeout')) {
      throw new Error('Request timed out. The video might be too long or the server is taking too long to respond.');
    }
    throw err;
  }
};

// Validate url and return video id if valid
export const getVideoId = function (url) {
  if (validateYouTubeUrl(url)) {
    const pattern =
      /^(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})/;
    const match = url.match(pattern);

    if (match) {
      return match[1]; // Return the extracted video ID
    } else {
      return null; // Return null if no match found
    }
  } else {
    return null; // Return null if url is not a valid YouTube URL
  }
};

const validateYouTubeUrl = function (url) {
  const pattern = /^(https?\:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.+$/;
  return pattern.test(url); // Returns true if URL matches the pattern, false otherwise
};
