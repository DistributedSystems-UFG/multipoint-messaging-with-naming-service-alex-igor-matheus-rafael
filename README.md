[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/YsEblNIV)

# Truco online UDP com Serviço de Nomes

Jogo de truco com comunicação UDP entre peers para a matéria de Sistemas Distribuídos.
A evolução desta versão adiciona um Serviço de Nomes simples usando ZeroMQ para remover a configuração estática dos endereços dos processos.

## Como rodar

1. Ligue 6 processos/máquinas: 1 Serviço de Nomes, 1 Group Manager e 4 peers.

2. Edite `constMP.py` e configure apenas `NAMING_SERVICE_ADDR` e `NAMING_SERVICE_PORT` com o endereço do Serviço de Nomes.

3. Clone o repositório nas máquinas ou no sistema de arquivos compartilhado `/mnt/efs/fs1/`.

4. Execute o Serviço de Nomes:

```bash
python3 namingService.py
```

5. Execute o `groupMngr.py` na máquina do servidor do jogo:

```bash
python3 groupMngr.py
```

6. Execute `peerComunicatorUDP.py` nas 4 máquinas peers:

```bash
python3 peerComunicatorUDP.py
```

7. Em cada um dos 4 peers, você controla as jogadas como se fosse um jogador.

Caso a descoberta automática de IP não encontre o endereço correto da máquina, defina a variável de ambiente `PROCESS_HOST` antes de iniciar o processo:

```bash
PROCESS_HOST=SEU_IP_PUBLICO python3 groupMngr.py
PROCESS_HOST=SEU_IP_PUBLICO python3 peerComunicatorUDP.py
```

## Como funciona

Cada peer é um jogador na mesa de truco. O Group Manager serve para iniciar cada rodada, manter o placar do jogo e distribuir as cartas, funcionando como um "dealer". Cada mão é jogada por comunicação direta entre os peers via UDP.

O Serviço de Nomes mantém os registros nome-endereço e tipo-nome. Ele oferece as operações:

- `bind(nome, endereco)`: cria um registro nome-endereço.
- `lookup(nome)`: retorna o endereço associado ao nome.
- `unbind(nome)`: remove um registro.
- `register(nome, tipo)`: associa um tipo a um nome já registrado.
- `discover(tipo)`: retorna todos os processos registrados com aquele tipo.

O único endereço estático configurado é o do Serviço de Nomes. O Group Manager registra seu endereço como `group-manager`, e os peers fazem `lookup("group-manager")` para encontrá-lo. Cada peer registra seu próprio endereço UDP como `peer-0`, `peer-1`, `peer-2` ou `peer-3`, associado ao tipo `peer`. Depois disso, cada peer usa `discover("peer")` para obter a lista de jogadores e enviar mensagens diretamente.

Peer <-> Peer: UDP | Peer <-> Group Manager: TCP | Processos <-> Serviço de Nomes: ZeroMQ.

## Relação com a ordenação das mensagens

A ordem das mensagens agora é essencial para manter a consistência da partida. Por exemplo, se um peer receber uma jogada do jogador 2 antes da jogada esperada do jogador 1, sua visão da mesa pode ficar incorreta. Isso pode causar erros na vez de jogar, no cálculo do vencedor da vaza ou no valor da mão.

Assim, a aplicação evidencia a importância da ordenação: em um jogo distribuído, todos os peers precisam processar os eventos na mesma sequência para manter o mesmo estado da partida.
