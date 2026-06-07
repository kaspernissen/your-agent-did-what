package com.example.store.tracing;

import jakarta.annotation.PostConstruct;
import org.springframework.context.annotation.Configuration;
import reactor.core.publisher.Hooks;

@Configuration(proxyBeanMethods = false)
public class ContextPropagationConfiguration {
    // Required when returning a Flux outside of Spring WebFlux to bridge
    // ThreadLocal context into the Reactor context for trace propagation.
    @PostConstruct
    void enableReactorContextPropagation() {
        Hooks.enableAutomaticContextPropagation();
    }
}
