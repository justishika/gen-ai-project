import axios from "axios";
import { API_URL, YOUTUBE_OEMBED_URL } from "./config";
import { getJSON } from "./helper";

export const state = {
    videoId: "",
    summary: "",
    title: "",
    thumbnailUrl: "",
    conversationHistory: [],
    insights: "",
    isQAMode: false
};

export const loadSummary = async function (summaryType = 'short') {
    try {
        const data = await getJSON(`${API_URL}/summary?v=${state.videoId}&type=${summaryType}`);

        // Check if the response has an error
        if (data.error) {
            throw new Error(data.data || "Unable to Summarize the video");
        }

        state.summary = data.data;
    } catch (err) {
        throw err;
    }
};

export const loadMetaData = async function (videoId) {
    try {
        const requestUrl = `${YOUTUBE_OEMBED_URL}?url=https://www.youtube.com/watch?v=${videoId}&format=json`;
        const result = await axios.get(requestUrl);
        state.title = result.data.title;
        state.thumbnailUrl = result.data.thumbnail_url;
    } catch (err) {
        throw err;
    }
};

export const askQuestion = async function (question) {
    try {
        const response = await axios.post(`${API_URL}/ask`, {
            video_id: state.videoId,
            question: question,
            history: state.conversationHistory
        });

        if (response.data.error) {
            throw new Error(response.data.data);
        }

        const answer = response.data.data;
        const metrics = response.data.metrics;

        // Add to conversation history
        state.conversationHistory.push({
            question: question,
            answer: answer,
            timestamp: new Date().toISOString()
        });

        return { answer, metrics };
    } catch (err) {
        throw err;
    }
};

export const loadInsights = async function () {
    try {
        const data = await getJSON(`${API_URL}/get-insights?v=${state.videoId}`);
        state.insights = data.data;
        return data.data;
    } catch (err) {
        throw err;
    }
};

export const extractEntities = async function () {
    try {
        const data = await getJSON(`${API_URL}/extract-entities?v=${state.videoId}`);

        if (data.error) {
            throw new Error(data.data || "Unable to extract entities");
        }

        return data.data;
    } catch (err) {
        throw err;
    }
};

export const clearConversation = function () {
    state.conversationHistory = [];
};

export const toggleQAMode = function () {
    state.isQAMode = !state.isQAMode;
};