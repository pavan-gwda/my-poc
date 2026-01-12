package com.ai.agent.tools;

import dev.langchain4j.agent.tool.Tool;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

/**
 * Calculator tool for the AI agent.
 *
 * The @Tool annotation tells LangChain4j:
 * 1. This method can be called by the LLM
 * 2. The description helps the LLM decide WHEN to use it
 * 3. Parameter names/types tell the LLM WHAT to pass
 */
@Component
public class CalculatorTool {

    private static final Logger log = LoggerFactory.getLogger(CalculatorTool.class);

    @Tool("Add two numbers together. Use this when you need to calculate a sum.")
    public double add(double a, double b) {
        log.info("TOOL CALLED: add({}, {})", a, b);
        return a + b;
    }

    @Tool("Subtract the second number from the first. Use for subtraction calculations.")
    public double subtract(double a, double b) {
        log.info("TOOL CALLED: subtract({}, {})", a, b);
        return a - b;
    }

    @Tool("Multiply two numbers. Use for multiplication calculations.")
    public double multiply(double a, double b) {
        log.info("TOOL CALLED: multiply({}, {})", a, b);
        return a * b;
    }

    @Tool("Divide the first number by the second. Use for division calculations.")
    public double divide(double a, double b) {
        log.info("TOOL CALLED: divide({}, {})", a, b);
        if (b == 0) {
            throw new IllegalArgumentException("Cannot divide by zero");
        }
        return a / b;
    }

    @Tool("Calculate the square root of a number.")
    public double squareRoot(double number) {
        log.info("TOOL CALLED: squareRoot({})", number);
        if (number < 0) {
            throw new IllegalArgumentException("Cannot calculate square root of negative number");
        }
        return Math.sqrt(number);
    }

    @Tool("Calculate a number raised to a power. First parameter is base, second is exponent.")
    public double power(double base, double exponent) {
        log.info("TOOL CALLED: power({}, {})", base, exponent);
        return Math.pow(base, exponent);
    }
}
