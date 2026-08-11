package com.capybara.sre.model;

import java.util.List;

public record ChatRequest(String prompt, List<Object> context, String model, List<Object> tools) {}
