# Fluxograma do algoritmo de verificação

O diagrama abaixo está em Mermaid e é renderizado automaticamente pelo GitHub.

```mermaid
flowchart TD
    A([Início]) --> B[/Ler telemetria do cenário/]
    B --> C[Inicializar lista de falhas vazia]
    C --> D{Temperatura interna<br/>entre 18 e 28 °C?}
    D -- Não --> D1[Registrar falha] --> E
    D -- Sim --> E{Temperatura externa<br/>entre -40 e 50 °C?}
    E -- Não --> E1[Registrar falha] --> F
    E -- Sim --> F{Pressão LOX<br/>entre 200 e 250 bar?}
    F -- Não --> F1[Registrar falha] --> G
    F -- Sim --> G{Pressão RP-1<br/>entre 190 e 240 bar?}
    G -- Não --> G1[Registrar falha] --> H
    G -- Sim --> H{Integridade<br/>estrutural = 1?}
    H -- Não --> H1[Registrar falha] --> I
    H -- Sim --> I{Nível de energia<br/>maior ou igual a 85%?}
    I -- Não --> I1[Registrar falha] --> J
    I -- Sim --> J{Todos os 5 módulos<br/>críticos em OK?}
    J -- Não --> J1[Registrar falha] --> K
    J -- Sim --> K[Calcular energia disponível,<br/>autonomia e margem]
    K --> L{Lista de falhas<br/>está vazia?}
    L -- Sim --> M([PRONTO PARA DECOLAR])
    L -- Não --> N([DECOLAGEM ABORTADA<br/>+ lista de motivos])
```

**Ponto central do desenho:** nenhuma resposta "Não" salta para o fim. Cada
verificação registra sua falha e segue para a próxima, de modo que o operador
receba a lista completa de problemas em uma única passagem — e não descubra um
problema por vez a cada tentativa de lançamento.
